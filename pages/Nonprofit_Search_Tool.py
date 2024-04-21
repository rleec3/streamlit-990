import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import re
from selenium.common.exceptions import NoSuchElementException

from io import BytesIO
import openpyxl



# Setup WebDriver for Selenium
def setup_driver():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Important for deployment in server environments
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# Function to fetch data
@st.cache_data
def fetch_data(ein):
    driver = setup_driver()
    url = f"https://projects.propublica.org/nonprofits/organizations/{ein}"
    driver.get(url)
    print(f"Accessing URL: {url}")

    # Allow page to load
    time.sleep(2)
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)  # Dismiss any popups

    # Initialize data dictionary
    data = {"EIN": ein}
    monetary_columns = ['Base Compensation', 'Bonus', 'Other Compensation', 'Deferred Compensation', 'Nontaxable Benefits', 'Total Compensation']

    try:
        # Attempt to click the 'View Filing' button
        view_filing_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn[href$="/full"]'))
        )
        ActionChains(driver).move_to_element(view_filing_button).perform()
        view_filing_button.click()
        print("View Filing button clicked")
        time.sleep(2)

        # Begin extraction of organizational data
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[src*='IRS990']")))
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='IRS990']")
        if iframes:
            driver.switch_to.frame(iframes[0])  # Switch to the first iframe that contains 'IRS990'

            # Extract the desired data now within the iframe 
            data.update({ 
                "990 Website": driver.current_url,
                "City": driver.find_element(By.CSS_SELECTOR, "span[id*='CityNm']").text,
                "State": driver.find_element(By.CSS_SELECTOR, "span[id*='StateAbbreviationCd']").text,
                "Organization Website": driver.find_element(By.CSS_SELECTOR, "span[id*='WebsiteAddressTxt']").text,
                "Mission": driver.find_element(By.CSS_SELECTOR, "span[id*='ActivityOrMissionDesc']").text,
                "Phone": driver.find_element(By.CSS_SELECTOR, "span[id*='PhoneNum']").text,
                "Gross Receipts": driver.find_element(By.CSS_SELECTOR, "span[id*='GrossReceiptsAmt']").text,
                "Business Name": driver.find_element(By.CSS_SELECTOR, "span[id*='BusinessName']").text,
                "Total Assets EOY": driver.find_element(By.CSS_SELECTOR, "span[id*='TotalAssetsEOYAmt']").text,
                "CY Total Expenses": driver.find_element(By.CSS_SELECTOR, "span[id*='CYTotalExpensesAmt'], span[id*='TotalExpensesRevAndExpnssAmt']").text,
                "CY Total Revenue": driver.find_element(By.CSS_SELECTOR, "span[id*='CYTotalRevenueAmt'], span[id*='TotalRevAndExpnssAmt']").text,
                "Fiscal Year End": driver.find_element(By.CSS_SELECTOR, "span[id*='TaxPeriodEndDt']").text,
                "Employee Count": driver.find_element(By.CSS_SELECTOR, "span[id*='TotalEmployeeCnt'], span[id*='OtherEmployeePaidOver50kCnt']").text,
            })
            print("Data Extracted")
            driver.refresh()
            #driver.switch_to.frame(iframe)
            # Calculate WYearEnd
            fiscal_year_end_text = data["Fiscal Year End"]
            if "-" in fiscal_year_end_text:
                fiscal_year_parts = fiscal_year_end_text.split("-")
                if len(fiscal_year_parts) == 3:
                    fiscal_year_month = int(fiscal_year_parts[0])
                    fiscal_year_year = int(fiscal_year_parts[2])
                    if fiscal_year_month == 12:
                        w_year_end = fiscal_year_end_text
                    else:
                        w_year_end = f"12-31-{fiscal_year_year - 1}"
                    data["WYearEnd"] = w_year_end
            # Additional logic for extracting compensation data goes here
                        # Additional extraction for compensation data
            time.sleep(2)  # Ensure all frames load properly
            
            compensation_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='IRS990ScheduleJ']")
            #people = []  # List to store all people's compensation data
            for iframe in compensation_iframes:
                driver.switch_to.frame(iframe)
                # Loop to gather all employee data available in the current iframe
                table = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "p2TbCtnr")))  # Change "tableId" to your actual table ID
                rows = table.find_elements(By.TAG_NAME, "tr")

                people = []
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")  # Assuming data is in <td> tags
                    if cols:  # Check if cols has elements to avoid empty rows
                        name_title = re.sub(r'^\d+', '', cols[0].text).split('\n')   # Split by newline character
                        name = name_title[0] if len(name_title) > 0 else ''
                        title = name_title[1] if len(name_title) > 1 else ''

                        def process_monetary_value(value):
                            # Split the value by dashes, remove commas, and filter out any empty values
                            numbers = [num.replace(',', '') for num in value.split('-') if num and num != '-']
                            # Convert to float and sum
                            total_value = sum(int(round(float(num))) for num in numbers if num not in ['-', ''])
                            return total_value

                        person_data = {
                            'Name': name.strip(),
                            'Title': title.strip(), 
                            'Base Compensation': process_monetary_value(cols[2].text),
                            'Bonus': process_monetary_value(cols[3].text),
                            'Other Compensation': process_monetary_value(cols[4].text),
                            'Deferred Compensation': process_monetary_value(cols[5].text),
                            'Nontaxable Benefits': process_monetary_value(cols[6].text),
                            'Total Compensation': process_monetary_value(cols[7].text),
                            # Add additional fields here as necessary
                        }
                        people.append(person_data)
                non_zero_people = [person for person in people if any(person.get(col, 0) != 0 for col in monetary_columns)]
                data['People'] = non_zero_people
                driver.switch_to.default_content()

    except Exception as e:
            print(f"Error during data extraction: {e}")
    finally:
            driver.quit()

    return data




# Streamlit UI Components

def edit_excel_template(data, template_path):
    workbook = openpyxl.load_workbook(template_path)
    sheet = workbook["Template"]  # Assumes that the sheet name is "Template"
    row = 9
    for entry in data:
        sheet[f"D{row}"] = entry["Organization_Name"]
        sheet[f"E{row}"] = entry["EIN"]
        sheet[f"F{row}"] = f"{entry['City']}, {entry['State']}"
        sheet[f"K{row}"] = entry["Employee_Name"]
        sheet[f"L{row}"] = entry["Title_Of_Position"]
        sheet[f"M{row}"] = entry["Base Compensation"]
        sheet[f"Q{row}"] = entry["Benefits and Deferred Compensation"]
        sheet[f"P{row}"] = entry["Other"]
        sheet[f"G{row}"] = entry["W2E"]
        sheet[f"H{row}"] = entry["Fiscal_Year_End"]
        sheet[f"J{row}"] = entry["Total Assets"]
        sheet[f"R{row}"] = entry["Nontaxable Benefits"]
        sheet[f"S{row}"] = entry["Total Compensation"]
        sheet[f"N{row}"] = entry["Bonus"]
        
        row += 1
    edited_file = BytesIO()
    workbook.save(edited_file)
    edited_file.seek(0)  # Move the cursor to the start of the stream
    return edited_file


if 'results' not in st.session_state:
    st.session_state['results'] = []

if 'final_chart_data' not in st.session_state:
    st.session_state.final_chart_data = []
st.header("Nonprofit Organization Data Fetcher")
ui.badges(badge_list=[ ("Under Construction", "destructive")], class_name="flex gap-2", key="main_badges1")
st.caption("Tip: Click the 3 dots dispalyed in the upper right hand corner > Settings > Enable Wide Mode to expand the view frame.")
if 'results' not in st.session_state:
    st.session_state['results'] = []
num_orgs = st.number_input("How many organizations do you want to fetch?", min_value=1, max_value=10, value=1)
ein_list = [st.text_input(f"Enter EIN {i+1}", key=i) for i in range(num_orgs)]
if st.button("Fetch Data"):
    with st.spinner("Fetching data..."):
        st.session_state['results'] = [fetch_data(ein) for ein in ein_list if ein.strip()]
# Displaying the fetched data and the organizational structure
if 'results' in st.session_state and st.session_state['results']:
    df = pd.DataFrame(st.session_state['results'])
    monetary_columns = ['Base Compensation', 'Bonus', 'Other Compensation', 'Deferred Compensation', 'Nontaxable Benefits', 'Total Compensation']
    for col in monetary_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0).apply(lambda x: round(float(x)))  # Ensure conversion to float, then round
    st.write(df)
    for result in st.session_state['results']:
        if 'Business Name' in result:
            st.subheader(result['Business Name'])
            if 'People' in result:
                people_df = pd.DataFrame(result['People'])
                st.table(people_df)
    # Creating a dropdown for each organization to select an employee
    selected_incumbents = {}
    for index, row in df.iterrows():
        if 'People' in row:
            employee_options = ['None'] + [
                f"{person['Name']} ({person['Title'] if person['Title'].strip() else 'Not Reported'})" 
                for person in row['People']
            ]
            selected_incumbent_key = f"employee-{row['EIN']}"
            selected_incumbent = st.selectbox(
                f"Select an employee for {row.get('Business Name', 'Unknown')}",
                employee_options,
                key=selected_incumbent_key
            )
            selected_incumbents[row['EIN']] = selected_incumbent
    # Button to generate the final output chart
    if st.button("Generate Final Output Chart"):
        final_chart_data = []
        for index, row in df.iterrows():
            if selected_incumbents.get(row['EIN']) and selected_incumbents[row['EIN']] != 'None':
                # Extract the name and title from the selected incumbent
                name_title = selected_incumbents[row['EIN']].split(' (')
                name = name_title[0]
                title = name_title[1].rstrip(')')
                selected_person_data = next(
                (person for person in row['People'] 
                 if f"{person['Name']} ({person['Title'] if person['Title'].strip() else 'Not Reported'})" == selected_incumbents[row['EIN']]), None
                )
            
                if selected_person_data:
                # Create a new row for the final chart
                    chart_row = {
                        "Organization_Name": row.get('Business Name', 'Unknown'),
                        "EIN": row['EIN'],
                        "Fiscal_Year_End": row.get('Fiscal Year End', ''),
                        "W2E": row.get('WYearEnd', ''),
                        "City": row.get('City', ''),
                        "State": row.get('State', ''),
                        "Employee_Name": name,
                        "Title_Of_Position": title,
                        "Total Assets": row.get('Total Assets EOY',''),
                        "Total Expenses": row.get('CY Total Expenses',''),
                        "Total Employees": row.get('Employee Count',''),
                        "Base Compensation": "${:,.0f}".format(selected_person_data.get('Base Compensation', 0)),
                        "Benefits and Deferred Compensation": "${:,.0f}".format(selected_person_data.get('Deferred Compensation', 0)),
                        "Other": "${:,.0f}".format(selected_person_data.get('Other Compensation', 0)),
                        "Total Compensation": "${:,.0f}".format(selected_person_data.get('Total Compensation', 0)),
                        "Bonus": "${:,.0f}".format(selected_person_data.get('Bonus', 0)),
                        "Nontaxable Benefits": "${:,.0f}".format(selected_person_data.get('Nontaxable Benefits', 0)),
                        # ... (other fields to include in the chart)
                    }
                    final_chart_data.append(chart_row)
        # Convert the final chart data to a DataFrame and display it
        final_df = pd.DataFrame(final_chart_data)
        st.write(final_df)

        
        # Create and download the Excel file within the same button condition
        if final_chart_data:
            edited_file = edit_excel_template(final_chart_data, '990TEMPLATE.xlsx')
            st.download_button(label="Download Updated 990 Template", data=edited_file, file_name="990_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if st.button("Reset Search"):
    st.session_state['results'] = []
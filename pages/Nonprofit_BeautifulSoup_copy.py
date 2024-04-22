import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to fetch years and corresponding URLs for the given EIN
def fetch_years(ein):
    base_url = "https://projects.propublica.org"
    url = f"{base_url}/nonprofits/organizations/{ein}"
    response = requests.get(url)
    years = {}
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        sections = soup.find_all("section", class_="single-filing-period")
        for section in sections:
            year = section['id'].replace("filing", "")
            links = section.find_all("a", class_="btn")
            xml_link = None
            for link in links:
                # Check if 'XML' is in the text, ignoring case
                if 'xml' in link.text.lower():
                    xml_link = link['href']
                    break
            if xml_link:
                years[year] = base_url + xml_link  # Concatenate base_url with the href attribute
            else:
                years[year] = "XML link not found"  # Handle cases where no XML link is found
    return years

#helper function to extract text 
def get_text(soup, selector):
    element = soup.select_one(selector)
    return element.text.strip() if element else "Not Available"


# Function to fetch detailed data from a URL associated with a selected year
def fetch_detailed_data(url):
    response = requests.get(url)
    data = {}
    if response.status_code == 200:
        # Parse the content as XML
        soup = BeautifulSoup(response.content, 'lxml-xml')
        
        # Extracting elements based on your provided XML structure
        data = {
            "990 Website": url,
            "City": soup.find('CityNm').text if soup.find('CityNm') else "Not Available",
            "State": soup.find('StateAbbreviationCd').text if soup.find('StateAbbreviationCd') else "Not Available",
            "Organization Website": soup.find('WebsiteAddressTxt').text if soup.find('WebsiteAddressTxt') else "Not Available",
            "Mission": soup.find('ActivityOrMissionDesc').text if soup.find('ActivityOrMissionDesc') else "Not Available",
            "Phone": soup.find('PhoneNum').text if soup.find('PhoneNum') else "Not Available",
            "Gross Receipts": soup.find('GrossReceiptsAmt').text if soup.find('GrossReceiptsAmt') else "Not Available",
            "Business Name": soup.find('BusinessNameLine1Txt').text if soup.find('BusinessNameLine1Txt') else "Not Available",
            "Total Assets EOY": soup.find('TotalAssetsEOYAmt').text if soup.find('TotalAssetsEOYAmt') else "Not Available",
            "CY Total Expenses": soup.find('CYTotalExpensesAmt').text if soup.find('CYTotalExpensesAmt') else "Not Available",
            "CY Total Revenue": soup.find('CYTotalRevenueAmt').text if soup.find('CYTotalRevenueAmt') else "Not Available",
            "Tax Period Begin": soup.find('TaxPeriodBeginDt').text if soup.find('TaxPeriodBeginDt') else "Not Available",
            "Fiscal Year End": soup.find('TaxPeriodEndDt').text if soup.find('TaxPeriodEndDt') else "Not Available",
            "Employee Count": soup.find('EmployeeCnt').text if soup.find('EmployeeCnt') else "Not Available",
        }
    return data



# Streamlit UI components
st.title("Nonprofit Organization Data Fetcher")
ein = st.text_input("Enter the EIN of the organization:")

if st.button("Load Available Years"):
        st.session_state.year_data = fetch_years(ein)
        st.write("Available years loaded. Now select a year.")

if 'year_data' in st.session_state and st.session_state.year_data:
    year_options = list(st.session_state.year_data.keys())
    selected_year = st.selectbox("Select a year", year_options)
    if selected_year:
        if st.button(f"Fetch Data for {selected_year}"):
            detailed_url = st.session_state.year_data[selected_year]
            st.session_state.selected_year_data = fetch_detailed_data(detailed_url)
            st.write(f"Detailed data fetched for the year {selected_year}:")
            st.json(st.session_state.selected_year_data)  # Display detailed data

# Reset functionality
if st.button("Reset"):
    st.session_state.year_data = {}
    st.session_state.selected_year_data = {}
    st.experimental_rerun()
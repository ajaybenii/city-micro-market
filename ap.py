from dotenv import load_dotenv
import os
import streamlit as st
import pandas as pd
from io import StringIO
from google import genai
from google.genai import types
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'

# Initialize Gemini client
gemini_client = genai.Client(
    http_options=types.HttpOptions(api_version="v1beta1"),
    vertexai=True,
    project='sqy-prod',
    location='global'
)

gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# --- Hardcoded CSV Data ---
CSV_DATA = """CItyName
Delhi
Gurgaon
Mumbai
Pune
Noida
"""

@st.cache_data
def load_csv_data():
    """Load and cache hardcoded CSV data"""
    try:
        df = pd.read_csv(StringIO(CSV_DATA))
        df.columns = df.columns.str.strip()
        if 'CItyName' not in df.columns:
            st.error("CSV data must contain 'CItyName' column")
            return None
        if df['CItyName'].isna().all():
            st.error("CItyName column contains no valid data")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading CSV data: {str(e)}")
        return None

def get_cities_from_csv(df):
    """Get unique cities from CSV"""
    if df is not None:
        cities = [city for city in df['CItyName'].unique().tolist() if pd.notna(city) and str(city).strip()]
        return sorted(cities)
    return []

# --- News Fetching Function ---
def fetch_news(city: str, start_date: str, end_date: str, prompt: str):
    """Fetch news for a specific city and its top localities within the specified time frame using Gemini"""
    try:
        categories = """
            new infrastructure developments or government projects (initiated or inaugurated), 
            urban or transport planning announcements (roads, metro, sewage, expressways, etc.), 
            road conditions, traffic disruptions, flooding, or damage, 
            water supply, drainage, or sewage problems, 
            public safety, electricity, or civic security concerns
        """
        
        query = prompt.format(
            start_date=start_date,
            end_date=end_date,
            city=city,
            categories=categories
        )
        print("Query:", query)
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=query,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=8192,
                system_instruction="""
                    You are a news curator.
                    Provide accurate, concise summaries of recent news from reliable sources, 
                    focusing only on the specified city and its specific localities or neighborhoods, 
                    and the specified categories. 

                    For each relevant story, include:
                    - City and a randomly generated, context-appropriate locality/neighborhood (ensure variety and relevance to the city)
                    - A clear 1-2 line summary of the issue or development
                    - Reporting date (YYYY-MM-DD)
                    - A reliable source link (must be correct and accessible)
                    
                    Format as a list with each item separated by a blank line. 
                    Only include news reported between {start_date} and {end_date} that fits the categories. 
                    Exclude older news, unrelated topics, or stories without specific locality details. 
                    Do not include FAQs, notes, or extra commentary.
                    Format the response cleanly for direct use on an organization page.
                """,
                temperature=0.7,
            )
        )
        
        content = response.text.strip()
        return content
    except Exception as e:
        return f"Error fetching news: {str(e)}"

# --- Streamlit App ---
def main():
    st.title("City News Generator")
    st.write("Generate news summaries for the last 7 days or daily related to infrastructure, transport, road conditions, water/sewage, or safety concerns for a city's specific localities.")

    # Load hardcoded CSV data
    csv_data = load_csv_data()

    # News Generation Form
    st.header("Generate News Summaries")
    default_prompt = """
        Fetch local civic and infrastructure news updates published from {start_date} to {end_date} 
        for the city of {city}, focusing on its specific localities or neighborhoods, 
        in the following categories: 
        New infrastructure developments or government projects (initiated or inaugurated), 
        Urban or transport planning announcements (roads, metro, sewage, expressways, etc.), 
        Road conditions, traffic disruptions, flooding, or damage, 
        Water supply, drainage, or sewage problems, 
        Public safety, electricity, or civic security concerns. 

        For each relevant story, include:
        - City and a randomly generated, context-appropriate locality/neighborhood
        - A 1-2 line summary of the issue/development
        - Reporting date (in YYYY-MM-DD format)
        - A reliable source link which should be original

        Only return news reported in the last 7 days that fits the categories. 
        Exclude older or unrelated topics.
        Format the response cleanly as a list with each item separated by a blank line for direct use on an organization page.
    """
    
    with st.form(key='news_form'):
        # City selection
        col1, col2 = st.columns([3, 2])
        with col1:
            available_cities = get_cities_from_csv(csv_data) if csv_data is not None else []
            selected_city = st.selectbox("Select City", [""] + available_cities, key="city_select")
        with col2:
            manual_city = st.text_input("Or Enter City Manually", key="city_input")
        
        # Use manual input if provided, otherwise use selected city
        city = manual_city.strip() if manual_city.strip() else selected_city
        
        # Time frame selection
        time_frame = st.radio("Select Time Frame:", ["Weekly (7 days)", "Daily (24 hours)"], index=0, key="time_frame")
        
        prompt = st.text_area("Edit News Prompt", default_prompt, height=300, key="news_prompt")
        submit = st.form_submit_button(label='Generate News Summaries')

    if submit and city:
        with st.spinner("Fetching news summaries..."):
            end_date = datetime.now().strftime("%Y-%m-%d")
            if time_frame == "Weekly (7 days)":
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            else:  # Daily (24 hours)
                start_date = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d")
            
            news_results = fetch_news(city, start_date, end_date, prompt)
            
            st.markdown("### News Summaries")
            if isinstance(news_results, str) and news_results.startswith("Error"):
                st.error(news_results)
            elif not news_results or news_results.lower().startswith("no relevant news found"):
                st.warning(f"No relevant news found for specific localities in {city} from {start_date} to {end_date}.")
            else:
                st.markdown(news_results)

if __name__ == "__main__":
    main()

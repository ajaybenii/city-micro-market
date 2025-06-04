from dotenv import load_dotenv
import os
import streamlit as st
import pyperclip
from google import genai
from google.genai import types
from docx import Document
from docx.shared import Pt
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'

# Initialize Gemini client
gemini_client = genai.Client(
    http_options=types.HttpOptions(api_version="v1beta1"),
    vertexai=True,
    project='sqy-prod',
    location='us-central1'
)

gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# --- City Description Function ---
def create_city_description(prompt: str, city: str) -> str:
    try:
        full_query = prompt.format(city=city)
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=full_query,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=8192,
                system_instruction="You are a helpful real-estate agent. Provide a response in plain text with Markdown syntax for bold headings (e.g., **Heading**) and no HTML tags, special characters, or FAQs. Do not include suggestions or notes in the response. Use data from Google Search tools to ensure accuracy and relevance.",
                temperature=0.7,
            )
        )
        content = response.text
        return content.strip()
    except Exception as e:
        return f"Error generating city description: {str(e)}"

# --- Micro Market Description Function ---
def create_micromarket_description(prompt: str, city: str, micromarket: str) -> str:
    try:
        full_query = prompt.format(city=city, micromarket=micromarket)
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=full_query,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=8192,
                system_instruction="You are a helpful real-estate agent. Provide a response in plain text with Markdown syntax for bold headings (e.g., **Heading**) and no HTML tags, special characters, or FAQs. Do not include suggestions or notes in the response. Use data from Google Search tools to ensure accuracy and relevance.",
                temperature=0.7,
            )
        )
        content = response.text
        return content.strip()
    except Exception as e:
        return f"Error generating micro market description: {str(e)}"

# --- Function to Create DOCX File ---
def create_docx(city_description: str = "", micromarket_description: str = "", city: str = "", micromarket: str = ""):
    doc = Document()
    # Set default font for the document
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Combine descriptions (city first, then micro market)
    combined_text = city_description
    if city_description and micromarket_description:
        combined_text += "\n\n" + micromarket_description
    elif micromarket_description:
        combined_text = micromarket_description

    if not combined_text:
        doc.add_paragraph("No descriptions available.")
    else:
        # Split combined text into lines
        lines = combined_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if the line is a heading (starts and ends with **)
            if line.startswith('**') and line.endswith('**'):
                # Add heading with bold formatting
                heading_text = line[2:-2].strip()  # Remove ** markers
                p = doc.add_paragraph()
                run = p.add_run(heading_text)
                run.bold = True
                run.font.size = Pt(14)  # Larger for headings
            else:
                # Add regular text or bullet points
                if line.startswith('- '):
                    # Bullet point
                    bullet_text = line[2:].strip()  # Remove '- '
                    p = doc.add_paragraph(style='List Bullet')
                    run = p.add_run(bullet_text)
                else:
                    # Regular paragraph
                    p = doc.add_paragraph()
                    run = p.add_run(line)

    # Save to BytesIO for download
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- Streamlit App ---
def main():
    st.title("City and Micro Market Description Generator")
    st.write("Generate city and micro market descriptions individually and download them combined in a single DOCX file.")

    # City description prompt
    city_prompt = """
    Provide a comprehensive description for city {city}. 
    Use data from Google Search tools to ensure accuracy, including relevant pincode details or other trending information where applicable.
    The description should cover:
    **{city} City Description**
    **Introduction**
    - Brief introduction to the city, including its location, significance, and key characteristics.
    **History**
    - Historical background, including key events or developments that shaped the city.
    **Economy**
    - Economic overview, highlighting major industries, business hubs, and economic challenges.
    **Demography**
    - Demographic details, including population, gender ratio, literacy rate, and notable demographic trends.
    **Infrastructure**
    - Highways: Major highways and roads ensuring connectivity.
    - Metro Routes: Key metro lines and stations for urban connectivity.
    - Rail Routes: Major railway stations and their connectivity.
    - Airport: Details of the nearest airport and its accessibility.
    **Top 20 Builders in {city}**
    - List the top 20 real estate builders operating in the city.
    **Top 10 Schools in {city}**
    - List the top 10 schools in the city.
    **Top 10 Hospitals in {city}**
    - List the top 10 hospitals in the city.
    **Top 10 Malls in {city}**
    - List the top 10 shopping malls in the city.
    Response Format
    - Use plain text with Markdown syntax for bold headings (e.g., **{city} City Description**, **Introduction**) and no HTML tags, special characters, or FAQs.
    - Structure the response with bold section headings using ** and regular text for other content (paragraphs, bullet points).
    - Use bullet points (denoted by '-') for lists.
    - Ensure proper spacing between sections and list items.
    - Use simple, natural, realistic language without embellishment.
    - Do not add notes, FAQs, or extra commentary.
    """

    # Micro market description prompt
    micromarket_prompt = """
    Provide a comprehensive description for micro market {micromarket} in city {city}. 
    Use data from Google Search tools to ensure accuracy, including relevant pincode details or other trending information where applicable.
    The description should cover:
    **{micromarket} Micro Market Description**
    - Provide a ~200-word description covering:
      - Unique selling points (connectivity, amenities, property rates, lifestyle).
      - Location within the city (describe relative to major roads, metro stations, or landmarks; include a placeholder for map integration).
    **Top 10 Real Estate Projects in {micromarket}**
    - List the top 10 real estate projects in {micromarket}, each with their unique selling points (connectivity, amenities, property rates, lifestyle).
    Response Format
    - Use plain text with Markdown syntax for bold headings (e.g., **{micromarket} Micro Market Description**) and no HTML tags, special characters, or FAQs.
    - Structure the response with bold section headings using ** and regular text for other content (paragraphs, bullet points).
    - Use bullet points (denoted by '-') for lists.
    - Ensure proper spacing between sections and list items.
    - Use simple, natural, realistic language without embellishment.
    - Do not add notes, FAQs, or extra commentary.
    """

    # City Description Form
    st.header("Generate City Description")
    with st.form(key='city_form'):
        city = st.text_input("City (e.g., Gurgaon)", key="city_input")
        city_prompt_area = st.text_area("Edit City Description Prompt", city_prompt, height=300, key="city_prompt")
        city_submit = st.form_submit_button(label='Generate City Description')

    if city_submit and city:
        with st.spinner("Generating city description..."):
            city_description = create_city_description(city_prompt_area, city)
            st.session_state['city_description'] = city_description
            st.session_state['city_name'] = city

    # Display city description if available
    if 'city_description' in st.session_state:
        st.markdown("### City Description")
        st.markdown(st.session_state['city_description'])
        if st.button("Copy City Description"):
            try:
                pyperclip.copy(st.session_state['city_description'])
                st.success("City description copied to clipboard!")
            except Exception as e:
                st.error(f"Failed to copy city description: {str(e)}")

    # Micro Market Description Form
    st.header("Generate Micro Market Description")
    with st.form(key='micromarket_form'):
        micro_city = st.text_input("City (e.g., Gurgaon)", key="micro_city_input")
        micromarket = st.text_input("Micro Market (e.g., Golf Course Road)", key="micromarket_input")
        micromarket_prompt_area = st.text_area("Edit Micro Market Description Prompt", micromarket_prompt, height=200, key="micromarket_prompt")
        micromarket_submit = st.form_submit_button(label='Generate Micro Market Description')

    if micromarket_submit and micro_city and micromarket:
        with st.spinner("Generating micro market description..."):
            micromarket_description = create_micromarket_description(micromarket_prompt_area, micro_city, micromarket)
            st.session_state['micromarket_description'] = micromarket_description
            st.session_state['micromarket_name'] = micromarket
            st.session_state['micro_city_name'] = micro_city

    # Display micro market description if available
    if 'micromarket_description' in st.session_state:
        st.markdown("### Micro Market Description")
        st.markdown(st.session_state['micromarket_description'])
        if st.button("Copy Micro Market Description"):
            try:
                pyperclip.copy(st.session_state['micromarket_description'])
                st.success("Micro market description copied to clipboard!")
            except Exception as e:
                st.error(f"Failed to copy micro market description: {str(e)}")

    # Download Combined DOCX
    if ('city_description' in st.session_state or 'micromarket_description' in st.session_state):
        st.header("Download Combined Description")
        city_desc = st.session_state.get('city_description', "")
        micro_desc = st.session_state.get('micromarket_description', "")
        city_name = st.session_state.get('city_name', "city")
        micro_name = st.session_state.get('micromarket_name', "micromarket")
        if st.button("Download Combined DOCX"):
            docx_buffer = create_docx(city_desc, micro_desc, city_name, micro_name)
            st.download_button(
                label="Download Combined Description as DOCX",
                data=docx_buffer,
                file_name=f"{micro_name}_{city_name}_description.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

if __name__ == "__main__":
    main()
import pdfplumber

text = ''
with pdfplumber.open(r'C:\Users\kalek\Downloads\Pune_IT_Freshers_Consultancies_Call_Tracker.pdf') as pdf:
    for page in pdf.pages:
        if page.extract_text():
            text += page.extract_text() + '\n'

with open('extracted_consultancies.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done')

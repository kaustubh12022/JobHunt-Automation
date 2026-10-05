import pymupdf

doc = pymupdf.open(r"C:\Users\kalek\Desktop\Resume_Dev_Updated (1).pdf")
page = doc[0]

search_text = "Final-year IT engineering student"
rects = page.search_for(search_text)

if rects:
    rect = rects[0]
    # Add a little padding to make sure we cover everything
    rect.x1 += 5
    
    # Redact the text
    page.add_redact_annot(rect, fill=(1, 1, 1)) # fill with white
    page.apply_redactions()
    
    # Insert new text.
    page.insert_text((rect.x0, rect.y1 - 2.5), "2026 Graduated Fresher - IT", fontname="Times-Roman", fontsize=10.012, color=(0,0,0))
    
    # Save directly over the original file, or to a new file?
    # The user said "On my desktop, there is a resume named “Dev Updated”... Change ONLY this part... Keep the formatting exactly as they are."
    # I should save it as the same file or rename the new one.
    # Let's save as Resume_Dev_Updated.pdf
    doc.save(r"C:\Users\kalek\Desktop\Resume_Dev_Updated.pdf")
    print("Successfully created modified PDF.")
else:
    print("Text not found.")

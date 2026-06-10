from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        # Logo or Header Text
        self.set_font('Arial', 'B', 15)
        self.set_text_color(30, 64, 175) # Blue color
        self.cell(0, 10, 'CareerMatch AI - ATS Evaluation Report', 0, 1, 'C')
        self.set_draw_color(200, 200, 200)
        self.line(10, 22, 200, 22)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')

def generate_pdf_report(data: dict, output_filepath: str):
    """
    Generates a PDF report based on the parsed resume data and role analysis.
    """
    pdf = PDFReport()
    pdf.add_page()

    # Extract data from the payload sent by React
    filename = data.get("filename", "Resume")
    predicted_role = data.get("predicted_role", "Unknown Role")
    ats_score = data.get("ats_score", 0)
    extracted_skills = data.get("extracted_skills", [])
    missing_skills = data.get("missing_skills", [])

    # Title Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Document: {filename}", 0, 1)
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(34, 197, 94) # Green
    pdf.cell(0, 10, f"Target Role: {predicted_role}", 0, 1)
    pdf.ln(5)

    # ATS Score Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "1. ATS Match Score", 0, 1)
    
    pdf.set_font('Arial', '', 11)
    if ats_score >= 75:
        pdf.set_text_color(34, 197, 94) # Green
    elif ats_score >= 50:
        pdf.set_text_color(234, 179, 8) # Yellow
    else:
        pdf.set_text_color(225, 29, 72) # Red
        
    pdf.cell(0, 10, f"Score: {ats_score}% Match for {predicted_role}", 0, 1)
    pdf.set_text_color(0, 0, 0) # Reset color
    pdf.ln(5)

    # Verified Skills Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. Verified Professional Skills (Found in Resume)", 0, 1)
    pdf.set_font('Arial', '', 11)
    
    if extracted_skills:
        skills_text = ", ".join([str(skill).title() for skill in extracted_skills])
        pdf.multi_cell(0, 8, skills_text)
    else:
        pdf.multi_cell(0, 8, "No core technical skills could be confidently extracted.")
    pdf.ln(5)

    # Missing Skills Section (Skill Gap)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "3. Identified Skill Gaps (Missing for this role)", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(225, 29, 72) # Red text for missing skills
    
    if missing_skills:
        missing_text = ", ".join([str(skill).title() for skill in missing_skills])
        pdf.multi_cell(0, 8, missing_text)
    else:
        pdf.set_text_color(34, 197, 94) # Green
        pdf.multi_cell(0, 8, "Excellent! You have all the core skills typically required for this role.")
    
    pdf.set_text_color(0, 0, 0) # Reset
    pdf.ln(10)

    # Next Steps / Recommendations
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "4. Recommendations & Next Steps", 0, 1)
    pdf.set_font('Arial', '', 11)
    
    recommendation = (
        f"To improve your chances of landing a {predicted_role} position, "
        f"consider upskilling in the missing technologies listed above. "
        f"Tailor your resume to include these keywords if you already possess the experience but forgot to list them."
    )
    pdf.multi_cell(0, 8, recommendation)

    # Output the PDF
    pdf.output(output_filepath)
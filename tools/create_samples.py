import os
import sys

def generate_samples():
    try:
        import fitz
    except ImportError:
        print("PyMuPDF (fitz) is not installed. Unable to generate sample PDFs.")
        return

    samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples")
    os.makedirs(samples_dir, exist_ok=True)

    samples = [
        {
            "filename": "Starbucks_Cease_And_Desist.pdf",
            "lines": [
                "STARBUCKS CORPORATION - LEGAL DEPARTMENT",
                "2401 Utah Avenue South, Seattle, WA 98134",
                "",
                "FORMAL NOTICE: CEASE AND DESIST TRADEMARK INFRINGEMENT",
                "Date: June 1, 2026",
                "",
                "To Whom It May Concern,",
                "",
                "It has come to our attention that your organization is displaying, marketing,",
                "and selling unauthorized merchandise bearing the Starbucks logo and trademarks,",
                "specifically retail coffee mugs and custom printed green aprons.",
                "",
                "This unauthorized use constitutes trademark infringement and dilution under federal laws.",
                "We hereby request you immediately cease and desist all unauthorized trademark use,",
                "remove all infringing items from your website, and destroy any remaining physical inventory.",
                "Please confirm your compliance in writing to this office within 10 business days.",
                "",
                "Sincerely,",
                "Starbucks Corporate Legal Services",
            ]
        },
        {
            "filename": "Acme_Invoice_Irrelevant.pdf",
            "lines": [
                "ACME INDUSTRIAL SOLUTIONS INC.",
                "100 Industrial Parkway, Chicago, IL 60607",
                "",
                "INVOICE #INV-2026-9812",
                "Date: May 15, 2026",
                "Due Date: June 15, 2026",
                "Billing To: Corporate Facilities Department",
                "",
                "Description of Services Rendered:",
                "1. Quarterly espresso machine maintenance and filter replacement: $120.00",
                "2. Standard coffee beans supply delivery (5 lbs pack): $30.00",
                "",
                "Subtotal: $150.00",
                "Sales Tax (0.0%): $0.00",
                "Total Amount Due: $150.00",
                "",
                "Thank you for your business! Please remit payment via bank transfer or check.",
            ]
        },
        {
            "filename": "SynergySphere_Ambiguous_Notice.pdf",
            "lines": [
                "SYNERGYSPHERE PROPERTY HOLDINGS",
                "500 Enterprise Way, Suite 300, San Francisco, CA 94105",
                "",
                "FORMAL NOTICE: GRADING OPERATIONS ON PROPERTY BOUNDARY",
                "Date: June 10, 2026",
                "",
                "Dear Neighbors,",
                "",
                "We are writing regarding the heavy grading and excavation operations currently occurring",
                "directly adjacent to our eastern boundary wall.",
                "",
                "Please suspend any excavation operations within five feet of our boundary wall",
                "until our structural engineers can review the ground vibration logs and site excavation maps.",
                "We wish to coordinate this review to avoid any damage to our foundation structures.",
                "Please contact our offices at property@synergysphere.com to organize a phone call.",
                "",
                "Best regards,",
                "SynergySphere Facilities Team",
            ]
        }
    ]

    for sample in samples:
        file_path = os.path.join(samples_dir, sample["filename"])
        doc = fitz.open()
        page = doc.new_page()
        
        y = 50
        for line in sample["lines"]:
            page.insert_text((50, y), line, fontsize=10)
            y += 18
            
        doc.save(file_path)
        doc.close()
        print(f"Generated sample PDF: {file_path}")

if __name__ == "__main__":
    generate_samples()

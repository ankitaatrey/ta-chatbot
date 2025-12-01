"""Script to create sample PDF files for demonstration."""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path


def create_biology_syllabus(filepath: Path):
    """Create a sample biology syllabus PDF."""
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    
    # Page 1
    c.setFont('Helvetica-Bold', 16)
    c.drawString(100, height - 100, 'Biology 101: Introduction to Cell Biology')
    c.setFont('Helvetica', 12)
    c.drawString(100, height - 140, 'Aarhus University - Fall 2025')
    c.drawString(100, height - 160, 'Instructor: Dr. Sarah Johnson')
    c.drawString(100, height - 180, 'Email: sarah.johnson@au.dk')
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 220, 'Course Description')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 250)
    text_object.textLines('''This course provides a comprehensive introduction to cell biology, covering
the fundamental structures and processes of cells. Students will explore
cell membrane structure and function, cellular organelles, protein synthesis,
and cell division. The course emphasizes both prokaryotic and eukaryotic cells,
with a focus on understanding the molecular basis of cellular life.

Topics include: cell membrane transport mechanisms, DNA replication and
transcription, translation and protein folding, mitochondrial function and
ATP synthesis, and the cell cycle including mitosis and meiosis.''')
    c.drawText(text_object)
    
    c.showPage()
    
    # Page 2
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 100, 'Learning Objectives')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 130)
    text_object.textLines('''By the end of this course, students will be able to:

1. Describe the structure and function of major cellular organelles
   including the nucleus, mitochondria, endoplasmic reticulum, and
   Golgi apparatus.

2. Explain the mechanisms of membrane transport including passive
   diffusion, facilitated diffusion, and active transport systems.

3. Understand the central dogma of molecular biology: DNA to RNA to protein.

4. Describe the processes of cell division including mitosis and meiosis.''')
    c.drawText(text_object)
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 350, 'Grading Policy')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 380)
    text_object.textLines('''Midterm Exam: 25%
Final Exam: 35%
Laboratory Work: 25%
Assignments and Quizzes: 15%

Attendance is mandatory for all laboratory sessions.''')
    c.drawText(text_object)
    
    c.showPage()
    
    # Page 3
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 100, 'Required Materials')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 130)
    text_object.textLines('''Textbook: Molecular Biology of the Cell, 7th Edition by Alberts et al.
Laboratory Manual: Available on the course website
Safety goggles and lab coat required for all laboratory sessions

Office Hours:
Tuesdays and Thursdays, 2-4 PM, Building 1252, Room 315''')
    c.drawText(text_object)
    
    c.save()


def create_physics_syllabus(filepath: Path):
    """Create a sample physics syllabus PDF."""
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    
    # Page 1
    c.setFont('Helvetica-Bold', 16)
    c.drawString(100, height - 100, 'Physics 201: Classical Mechanics')
    c.setFont('Helvetica', 12)
    c.drawString(100, height - 140, 'Aarhus University - Fall 2025')
    c.drawString(100, height - 160, 'Instructor: Prof. Lars Nielsen')
    c.drawString(100, height - 180, 'Email: lars.nielsen@au.dk')
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 220, 'Course Overview')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 250)
    text_object.textLines('''This course covers the fundamental principles of classical mechanics,
including Newtonian mechanics, energy and momentum conservation, rotational
motion, and oscillations. Students will develop problem-solving skills and
learn to apply mathematical techniques to physical problems.

Key topics include: kinematics in one and two dimensions, Newton's laws of
motion and their applications, work and kinetic energy, potential energy and
conservation of energy, linear momentum and collisions, rotational kinematics
and dynamics, angular momentum, and simple harmonic motion.''')
    c.drawText(text_object)
    
    c.showPage()
    
    # Page 2
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 100, 'Problem-Solving Approach')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 130)
    text_object.textLines('''Recommended problem-solving strategy:

1. Read the problem carefully and identify the given information.
2. Draw a diagram or sketch showing the physical situation.
3. Identify the relevant physics principles and equations.
4. Solve algebraically before substituting numerical values.
5. Check that your answer has the correct units and makes physical sense.

Weekly problem sets will be assigned and are due on Fridays by 5 PM.''')
    c.drawText(text_object)
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 380, 'Assessment')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 410)
    text_object.textLines('''Problem Sets: 20%
Midterm Exam 1: 20%
Midterm Exam 2: 20%
Final Exam: 40%

All exams are closed-book but you may bring one page of handwritten notes.''')
    c.drawText(text_object)
    
    c.save()


def create_policies_pdf(filepath: Path):
    """Create a sample course policies PDF."""
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    
    # Page 1
    c.setFont('Helvetica-Bold', 16)
    c.drawString(100, height - 100, 'General Course Policies - AU')
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 150, 'Academic Integrity')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 180)
    text_object.textLines('''All students are expected to maintain the highest standards of academic
integrity. This includes: completing all work independently unless
collaboration is explicitly permitted, properly citing all sources used in
written work, not sharing exam questions or solutions with other students,
and not using unauthorized materials during exams.

Violations of academic integrity will result in serious consequences.''')
    c.drawText(text_object)
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 350, 'Attendance and Participation')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 380)
    text_object.textLines('''Regular attendance is expected and will contribute to your success in the
course. If you must miss a class, please notify the instructor in advance.
You are responsible for obtaining notes and materials from missed classes.

Active participation in class discussions and activities is encouraged.''')
    c.drawText(text_object)
    
    c.showPage()
    
    # Page 2
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 100, 'Extensions and Late Work')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 130)
    text_object.textLines('''Extensions may be granted for documented medical emergencies or other
serious circumstances. Requests for extensions must be made before the
deadline whenever possible.

Late work will generally receive a penalty unless an extension has been
granted. For exams, makeup exams will only be given in cases of documented
emergencies.''')
    c.drawText(text_object)
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, height - 300, 'Accommodation for Disabilities')
    c.setFont('Helvetica', 11)
    text_object = c.beginText(100, height - 330)
    text_object.textLines('''Students with disabilities who need accommodations should contact the
instructor and the university disability services office at the beginning
of the semester. Appropriate accommodations will be arranged in accordance
with university policy.''')
    c.drawText(text_object)
    
    c.save()


def main():
    """Create all sample PDFs."""
    # Create directory
    data_dir = Path('data/sample')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating sample PDFs...")
    
    # Create PDFs
    create_biology_syllabus(data_dir / 'syllabus_bio.pdf')
    print("  ✓ Created syllabus_bio.pdf")
    
    create_physics_syllabus(data_dir / 'syllabus_physics.pdf')
    print("  ✓ Created syllabus_physics.pdf")
    
    create_policies_pdf(data_dir / 'course_policies.pdf')
    print("  ✓ Created course_policies.pdf")
    
    print("\nSample PDFs created successfully in data/sample/")
    print("Run 'python -m src.ingestion --data_dir data/sample' to ingest them.")


if __name__ == "__main__":
    main()


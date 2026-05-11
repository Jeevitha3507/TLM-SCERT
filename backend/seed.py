"""
Seed script: generates 150 mock teachers, Tamil Nadu schools, and sample posts.
Run: python seed.py
"""
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, engine, Base
from models import School, Teacher, Student, Post, Metric
from auth import hash_password

DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
    "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam",
    "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram",
    "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni",
    "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
    "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore",
    "Villupuram", "Virudhunagar", "Kanyakumari",
]

# District index map for UDISE generation (33 = TN state code)
DISTRICT_CODES = {d: str(i + 1).zfill(2) for i, d in enumerate(DISTRICTS)}

SUBJECTS = [
    "Mathematics", "Science", "Social Science", "Tamil", "English",
    "Physics", "Chemistry", "Biology", "History", "Geography",
]

FIRST_NAMES = [
    "Murugan", "Karthik", "Selvam", "Rajan", "Suresh", "Ramesh", "Vijay",
    "Arun", "Senthil", "Mani", "Balan", "Durai", "Kumar", "Arjun", "Siva",
    "Pandian", "Anand", "Gopi", "Sundar", "Prabhu", "Chandran", "Nathan",
    "Velu", "Thiru", "Ganesh", "Mohan", "Dinesh", "Balaji", "Manoj",
    "Prakash", "Venkat", "Gopal", "Rajesh", "Ashok", "Sathish", "Vinoth",
    "Baskaran", "Kalai", "Arul", "Muthu", "Vignesh", "Vasanth", "Kamal",
    "Saravanan", "Perumal", "Ilango", "Dhanaraj", "Subramanian", "Raghu",
    "Jayakumar", "Priya", "Lakshmi", "Meenakshi", "Kavitha", "Valli",
    "Malathi", "Sumathi", "Usha", "Kamala", "Bharathi", "Rekha", "Nirmala",
    "Vasantha", "Radha", "Lalitha", "Chitra", "Geetha", "Indira", "Mala",
    "Vijayalakshmi", "Padmavathi", "Saranya", "Deepa", "Revathi", "Sowmya",
    "Anitha", "Kalpana", "Nithya", "Suganya", "Thenmozhi", "Ambika",
    "Eswari", "Jothi", "Kokila", "Mangai", "Nalini", "Oviya", "Pavithra",
    "Rani", "Selvi", "Tamilarasi", "Uma", "Vanitha", "Yamuna", "Mythili",
    "Poornima", "Hemamalini", "Sakunthala", "Bhavani", "Komathi", "Devi",
    "Muthulakshmi", "Rajeswari", "Thilagavathi", "Kanimozhi", "Arulmozhi",
]

LAST_NAMES = [
    "Murugesan", "Krishnan", "Subramanian", "Ramasamy", "Velusamy",
    "Muthusamy", "Shanmugam", "Chandrasekaran", "Arumugam", "Balakrishnan",
    "Sundaram", "Venkatesan", "Ramachandran", "Govindasamy", "Ponnusamy",
    "Mahalingam", "Paramasivam", "Annamalai", "Somasundaram", "Palanisamy",
    "Natarajan", "Selvaraj", "Pandian", "Rajan", "Durai", "Kannan",
    "Srinivasan", "Periyasamy", "Rathinam", "Thangavel", "Rajendhiran",
    "Karuppasamy", "Senthilkumar", "Rajendran", "Palaniswamy", "Soundarrajan",
]

# Realistic TN school name patterns
SCHOOL_PATTERNS = [
    ("Government", "Higher Secondary School"),
    ("Government Girls", "Higher Secondary School"),
    ("Government Boys", "Higher Secondary School"),
    ("Government Model", "Higher Secondary School"),
    ("Panchayat Union", "Middle School"),
    ("Panchayat Union", "Elementary School"),
    ("Municipal", "Higher Secondary School"),
    ("Corporation", "High School"),
    ("Government Adi Dravidar Welfare", "Higher Secondary School"),
    ("Government Tribal Welfare", "High School"),
    ("Government", "High School"),
    ("Presidency Girls", "Higher Secondary School"),
    ("Nehru Memorial Government", "Higher Secondary School"),
    ("Anna Memorial Government", "Higher Secondary School"),
]

# Realistic TLM method descriptions — detailed, Tamil Nadu context
TLM_METHODS = [
    "Prepared a papier-mâché globe using waste newspaper to teach longitude and latitude. Students coloured land and water bodies, then marked Tamil Nadu districts with small flag pins.",
    "Made fraction kits using ice-cream sticks and coloured paper. Students physically combined pieces to understand equivalent fractions and addition of unlike fractions for Grade 6.",
    "Created a working periscope model using cardboard tubes and small mirrors to demonstrate the laws of reflection in Grade 8 Science.",
    "Designed a Tamil alphabet 'snake and ladder' board game where each square has a letter. Students learnt alphabetical order while playing collaboratively.",
    "Used seed germination in transparent zip-lock bags to teach plant biology. Each student observed their plant daily and recorded observations in a journal for two weeks.",
    "Made a mnemonic wall chart pairing Tamil proverbs with their meanings, helping students build vocabulary in their mother tongue through cultural context.",
    "Prepared a 'Math Story' booklet showing multiplication as repeated addition using pictures of market items — mangoes, bananas, coconuts — familiar to rural students.",
    "Created paper bag puppets of freedom fighters like Kattabomman and Rani Velu Nachiyar to dramatise Tamil Nadu's freedom struggle for Grade 6 History.",
    "Made a working model of a water purification system using sand, gravel, and charcoal layers in plastic bottles to demonstrate natural filtration.",
    "Prepared a weather wheel spinner with seasonal Tamil names. Students spun daily, recorded weather, and created a monthly data chart — building statistical literacy.",
    "Used real currency notes and coins to teach decimal concepts and percentage calculations. Students ran a mock bazaar where they calculated profit and loss in Grade 7.",
    "Created a timeline mural on the classroom wall from Sangam era to modern times. Students drew historical figures and placed them on the timeline using Tamil historical dates.",
    "Made a 3D clay map of Tamil Nadu with districts raised in relief. Rivers were modelled with blue clay; students identified their home districts and local water bodies.",
    "Prepared human body outline posters where students placed organ cutouts in correct positions and labelled them in both Tamil and English.",
    "Created an 'adjective auction' activity with picture cards where students bid using play money to describe objects in English, building descriptive vocabulary in a fun way.",
    "Made a rope number line stretched across the classroom. Students physically stood on integers to solve addition and subtraction problems, making abstract numbers concrete.",
    "Prepared a solar system mobile with paper balls painted as planets, hung proportionally from the ceiling. Students measured and compared planet sizes and distances.",
    "Created a periodic table poster with Tamil names for common elements — iron as 'இரும்பு', gold as 'தங்கம்'. Students identified everyday items containing each element.",
    "Made a traditional Kolam dot pattern activity connecting dots with lines to teach geometric symmetry and patterns, connecting Mathematics with Tamil cultural art.",
    "Prepared sentence-building card sets with Tamil subjects, verbs, and objects that students assembled like puzzle pieces to form grammatically correct Tamil sentences.",
    "Created a Tamil Nadu industries map using pictures from old magazines. Students identified industries, their districts, and discussed raw material sources and transport.",
    "Made angle measurers using two rulers joined with a brass fastener. Students measured angles of classroom objects and classified them as acute, obtuse, right, or reflex.",
    "Prepared a 'life cycle wheel' spinner showing butterflies, frogs, and plants. Students spun, drew the organism, and labelled each stage — egg, larva, pupa, adult.",
    "Created a 'newspaper mathematics' activity where students found advertised prices, calculated percentage discounts, and summed total shopping bills from actual newspaper ads.",
    "Made a model of a traditional Tamil Nadu tiled-roof house using matchboxes and clay tiles. Students compared architectural features with modern RCC constructions.",
    "Prepared a colour-coded district map of Tamil Nadu where each district is a separate laminated card. Students assembled the puzzle to build geographic knowledge of the state.",
    "Used locally collected leaves, seeds, and soil samples to create a biodiversity chart. Students classified flora by leaf shape, seed type, and habitat using a dichotomous key.",
    "Made a simple electric buzzer circuit using a 9V battery, wire, and a buzzer to demonstrate series and parallel circuits. Students then designed their own circuit diagrams.",
    "Prepared a bilingual story-sequencing activity with picture cards showing a traditional Tamil folk tale. Students arranged cards, narrated the story, and wrote a summary.",
    "Created a rain gauge from a cut plastic bottle and ruler to measure local rainfall. Students recorded data for a month and compared with Tamil Nadu meteorological records.",
]

SAMPLE_TITLES = {
    "Mathematics": [
        "Fractions Made Easy with Coloured Paper Kits",
        "Understanding Geometry with Geoboard Activity",
        "Multiplication Tables Chart and Chanting Game",
        "Algebra Basics with Balance Beam Model",
        "Number Patterns with Matchstick Puzzles",
        "Area and Perimeter Real-Life Measurement",
        "Percentage and Profit-Loss Market Game",
        "Angles in Real Life — Classroom Measurement",
        "Place Value Kit with Beads and Abacus",
        "Integer Addition with Classroom Number Line",
    ],
    "Science": [
        "Plant Cell Model using Thermocol Sheet",
        "Water Cycle Demonstration in a Closed Box",
        "States of Matter — Ice, Water, Steam Activity",
        "Food Chain Activity with Picture Cards",
        "Simple Machines Found in Our Kitchen",
        "Photosynthesis Chart and Leaf Colour Test",
        "Human Digestive System Paper Model",
        "Electricity Circuit Board — Series & Parallel",
        "Seed Germination 14-Day Observation Journal",
        "Water Purification Model using Natural Materials",
    ],
    "Tamil": [
        "Tamil Alphabets Chart with Rhyme Cards",
        "Poetry Recitation Aid — Thirukkural Poster",
        "Tamil Grammar Rules with Colour-Coded Cards",
        "Story Illustration — Panchatantra in Tamil",
        "Compound Words Puzzle Activity (சொல் இணைப்பு)",
        "Tamil Proverbs Wall Chart with Meanings",
        "Sentence Building Cards — Subject Verb Object",
        "Tamil Districts Song and Map Activity",
    ],
    "English": [
        "English Alphabets Flash Cards with Pictures",
        "Tense Chart — Past Present Future",
        "Vocabulary Builder with Word-Picture Match",
        "Reading Comprehension Aid with Question Strips",
        "Grammar Activity — Parts of Speech Sorting",
        "Adjective Auction — Descriptive Vocabulary Game",
        "Phonics Wall Chart for Grade 3–4",
        "Story Sequencing Cards — Folk Tale",
    ],
    "Social Science": [
        "Puzzle Map of Tamil Nadu Districts",
        "Rivers and Dams of Tamil Nadu Chart",
        "Tamil Nadu History Timeline Mural",
        "Government Structure — Three Tiers Diagram",
        "Indian Constitution — Fundamental Rights Poster",
        "Freedom Fighters of Tamil Nadu Gallery",
        "Panchayat System Skit and Role Play",
        "Natural Resources Map of Tamil Nadu",
    ],
    "Physics": [
        "Laws of Motion with Trolley Demonstration",
        "Optics — Periscope and Mirror Experiment",
        "Electricity Circuit Board Model",
        "Sound Wave Chart with Tuning Fork",
        "Force and Pressure — Balloon Activity",
        "Archimedes Principle — Water Displacement Demo",
        "Simple Pendulum — Time Period Measurement",
    ],
    "Chemistry": [
        "Periodic Table Chart with Tamil Element Names",
        "Chemical Bonding Model — Ball and Stick",
        "Acid-Base Indicator with Turmeric Paper",
        "Organic Chemistry — Carbon Chain Models",
        "Electrolysis Demonstration — Salt Water",
        "Rust Formation — Iron Nail Activity",
    ],
    "Biology": [
        "Human Body Systems — Organ Placement Activity",
        "Cell Structure Model — Animal and Plant",
        "Genetics Chart — Mendel's Pea Experiment",
        "Ecosystem Food Web — Local Animals",
        "Biodiversity Chart — Local Leaf Collection",
        "Photosynthesis and Respiration Comparison Chart",
    ],
    "History": [
        "Ancient Tamil Kingdoms Timeline — Sangam to Modern",
        "Freedom Fighters Gallery — Tamil Nadu Heroes",
        "Mughal Empire Map and Trade Route Activity",
        "World War II Timeline and Impact Chart",
        "Ancient Tamil Trade Routes Illustrated Map",
        "Tamil Nadu Under British Rule — Event Cards",
    ],
    "Geography": [
        "Physical Map of Tamil Nadu — Clay Relief Model",
        "Climate Zones Chart — India Seasonal Map",
        "Soil Types Display with Local Samples",
        "Natural Resources Map — Minerals and Forests",
        "Population Distribution Chart — Tamil Nadu",
        "River Systems of South India — Flow Map",
        "Rain Gauge — Monthly Rainfall Measurement",
    ],
}


def random_date(start_days_ago=180):
    return datetime.utcnow() - timedelta(days=random.randint(0, start_days_ago))


def gen_udise(district_code: str, block: int, serial: int) -> str:
    """Generate a realistic 11-digit Tamil Nadu UDISE code: 33 + DD + BB + SSSSS"""
    block_code = str(block).zfill(2)
    school_serial = str(serial).zfill(5)
    return f"33{district_code}{block_code}{school_serial}"


def make_school_name(district: str) -> str:
    prefix, level = random.choice(SCHOOL_PATTERNS)
    if level:
        return f"{prefix} {level}, {district}"
    return f"{prefix}, {district}"


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Teacher).count() > 0:
            print("Database already seeded. Skipping.")
            return

        print("Creating admin account...")
        admin_school = School(
            udise_code="33030100001",
            name="SCERT Tamil Nadu, Chennai",
            district="Chennai",
        )
        db.add(admin_school)
        db.flush()

        admin = Teacher(
            emis_id=os.getenv("ADMIN_EMIS_ID", "SCERT001"),
            name="SCERT Administrator",
            password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "scert@admin123")),
            school_id=admin_school.id,
            district="Chennai",
            subject=None,
            is_admin=True,
        )
        db.add(admin)
        db.flush()

        print("Creating 150 teachers with schools...")
        teachers = []
        for i in range(1, 151):
            district = DISTRICTS[(i - 1) % len(DISTRICTS)]
            dist_code = DISTRICT_CODES[district]
            block = random.randint(1, 15)
            udise = gen_udise(dist_code, block, i)

            school_name = make_school_name(district)
            school = School(udise_code=udise, name=school_name, district=district)
            db.add(school)
            db.flush()

            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            subject = random.choice(SUBJECTS)
            emis_id = str(10000000 + i)   # 8-digit numeric EMIS ID

            teacher = Teacher(
                emis_id=emis_id,
                name=f"{first} {last}",
                password_hash=hash_password("teacher@123"),
                school_id=school.id,
                district=district,
                subject=subject,
                is_admin=False,
                created_at=random_date(365),
            )
            db.add(teacher)
            db.flush()
            teachers.append(teacher)

        print("Creating 200 sample students...")
        grade_list = list(range(6, 13))
        for j in range(1, 201):
            school = random.choice(teachers).school
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            student = Student(
                emis_number=f"ST{str(j).zfill(7)}",
                name=f"{first} {last}",
                school_id=school.id if school else None,
                grade=random.choice(grade_list),
                created_at=random_date(365),
            )
            db.add(student)

        db.flush()

        print("Creating sample posts (random distribution)...")
        for teacher in teachers:
            num_posts = random.randint(1, 5)
            subject = teacher.subject or random.choice(SUBJECTS)
            title_pool = SAMPLE_TITLES.get(subject, ["TLM Activity", "Teaching Aid", "Learning Material"])

            for _ in range(num_posts):
                title = random.choice(title_pool)
                grade = random.choice(grade_list)
                post = Post(
                    teacher_id=teacher.id,
                    title=title,
                    subject=subject,
                    grade=grade,
                    tlm_method=random.choice(TLM_METHODS),
                    file_type=random.choice(["image", "document", "video", "audio"]),
                    file_url=None,
                    original_filename=None,
                    created_at=random_date(180),
                )
                db.add(post)
                db.flush()

                metric = Metric(
                    post_id=post.id,
                    view_count=random.randint(5, 600),
                    like_count=random.randint(0, 100),
                    download_count=random.randint(0, 60),
                    comment_count=random.randint(0, 35),
                )
                db.add(metric)

        # ── 20 hand-crafted showcase posts from specific schools ──────────────
        print("Creating 20 showcase posts...")
        SHOWCASE = [
            ("Presidency Girls Higher Secondary School, Chennai", "Chennai",
             "Tamil", 10, "Tamil Kamban Ramayana — Illustrated Story Boards",
             "Prepared 12 illustrated story boards depicting key scenes from Kamban Ramayana. Each board has the original Tamil verse, a simplified explanation, and student artwork."),
            ("Government Boys Higher Secondary School, Coimbatore", "Coimbatore",
             "Mathematics", 11, "Differentiation & Integration Visual Chart",
             "Made laminated wall charts showing differentiation rules with colour-coded worked examples. Students used sticky notes to add their own examples after each lesson."),
            ("Panchayat Union Middle School, Thanjavur", "Thanjavur",
             "Science", 7, "Thanjavur Soil Types — Field Collection Activity",
             "Collected soil samples from 4 locations near Thanjavur — riverbank, paddy field, upland, and garden. Students compared texture, water retention, and colour."),
            ("Corporation High School, Madurai", "Madurai",
             "Social Science", 8, "Madurai Meenakshi Temple — Architecture Study",
             "Created a scale model of a gopuram using clay. Students researched Dravidian architecture and presented findings on how ancient temples served as community centres."),
            ("Government Model Higher Secondary School, Salem", "Salem",
             "English", 9, "Newspaper Reading Club — Weekly Current Affairs",
             "Started a weekly newspaper reading activity. Students summarised one article in English, identified new vocabulary, and discussed the topic for 15 minutes."),
            ("Government Girls Higher Secondary School, Tiruchirappalli", "Tiruchirappalli",
             "Biology", 12, "DNA Extraction from Banana — Lab Activity",
             "Extracted DNA from banana cells using dish soap, salt water, and ethyl alcohol. Students observed white DNA strands in the alcohol layer and sketched the result."),
            ("Government Higher Secondary School, Vellore", "Vellore",
             "History", 10, "Vellore Mutiny 1806 — Event Reconstruction",
             "Students researched the Vellore Mutiny and created an event newspaper 'Vellore Gazette 1806'. Each student wrote one article — cause, event, aftermath, or significance."),
            ("Panchayat Union Elementary School, Erode", "Erode",
             "Tamil", 5, "Thiruvalluvar Kural — Memorisation Flash Cards",
             "Made 30 laminated flash cards each with one Kural couplet on front and meaning + application in daily life on back. Class competed to memorise the most Kurals in a week."),
            ("Government Adi Dravidar Welfare HSS, Thoothukudi", "Thoothukudi",
             "Science", 6, "Pearl Oyster — Fishing Community Science",
             "Connected the science lesson on shells and organisms to local pearl fishing heritage. Students collected empty oyster shells and studied their structure under magnification."),
            ("Government Higher Secondary School, Kanyakumari", "Kanyakumari",
             "Geography", 9, "Convergence of Three Seas — Local Geography Study",
             "Made a map showing Kanyakumari's position at the tip of the peninsula where the Bay of Bengal, Arabian Sea, and Indian Ocean meet. Students measured tidal variations."),
            ("Government Boys HSS, Namakkal", "Namakkal",
             "Mathematics", 8, "Namakkal Lorry Transport — Rate Problems",
             "Used Namakkal's famous lorry industry as context for distance-speed-time problems. Students calculated fuel costs, delivery times, and profit margins for sample routes."),
            ("Government Higher Secondary School, Nilgiris", "Nilgiris",
             "Biology", 10, "Nilgiris Biodiversity Chart — Endemic Species",
             "Created a chart of 20 endemic plants and animals of the Nilgiris Biosphere Reserve including Shola forests, Toda community plants, and migratory birds with illustrations."),
            ("Municipal Higher Secondary School, Chennai", "Chennai",
             "Physics", 11, "Simple Harmonic Motion — Pendulum Lab",
             "Students made pendulums using string and clay balls of different masses. They measured time periods for different lengths and plotted T² vs L to find g experimentally."),
            ("Government Model HSS, Coimbatore", "Coimbatore",
             "Chemistry", 12, "Coimbatore Textile Dyes — Chemistry of Colour",
             "Connected organic chemistry to Coimbatore's textile industry. Students tested fabric samples with acid/base indicators to understand synthetic dye behaviour."),
            ("Panchayat Union Middle School, Sivaganga", "Sivaganga",
             "Social Science", 7, "Sivaganga Kingdom — Velu Nachiyar Story",
             "Made a comic strip telling the story of Queen Velu Nachiyar and her fight against British rule. Students researched facts and drew each panel, then presented to the class."),
            ("Government Girls HSS, Tirunelveli", "Tirunelveli",
             "English", 10, "Tirunelveli Halwa — Process Writing Activity",
             "Used the famous Tirunelveli halwa recipe as a stimulus for process writing in English. Students wrote step-by-step instructions, used passive voice, and sequencing words."),
            ("Government Higher Secondary School, Dindigul", "Dindigul",
             "Mathematics", 9, "Dindigul Lock Industry — Applied Geometry",
             "Studied the geometry of lock mechanisms. Students measured angles, identified geometric shapes in lock components, and calculated gear ratios as a practical application."),
            ("Government Tribal Welfare High School, Dharmapuri", "Dharmapuri",
             "Science", 8, "Forest Ecosystem — Dharmapuri Hills Study",
             "Students collected leaf, bark, and soil samples from the local forest on a guided walk. They identified 10 tree species, described their roles in the ecosystem, and made a chart."),
            ("Corporation High School, Tiruvallur", "Tiruvallur",
             "Tamil", 8, "Modern Tamil Short Story — Reading and Discussion",
             "Selected three short stories by contemporary Tamil writers. Students read aloud, identified narrative techniques, character motivations, and wrote a 200-word critical response."),
            ("Government Higher Secondary School, Villupuram", "Villupuram",
             "Geography", 11, "Cauvery Delta Agriculture — Land Use Mapping",
             "Used satellite image printouts of the Cauvery delta region to identify paddy fields, canals, roads, and settlements. Students created a hand-drawn land use map with a legend."),
        ]

        for school_name, district, subject, grade, title, method in SHOWCASE:
            dist_code = DISTRICT_CODES.get(district, "01")
            udise = gen_udise(dist_code, random.randint(1, 15), 9000 + len(SHOWCASE))

            school = School(udise_code=udise, name=school_name, district=district)
            db.add(school)
            db.flush()

            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            showcase_teacher = Teacher(
                emis_id=str(20000000 + len(teachers) + 1),
                name=f"{first} {last}",
                password_hash=hash_password("teacher@123"),
                school_id=school.id,
                district=district,
                subject=subject,
                is_admin=False,
                created_at=random_date(365),
            )
            db.add(showcase_teacher)
            db.flush()
            teachers.append(showcase_teacher)

            post = Post(
                teacher_id=showcase_teacher.id,
                title=title,
                subject=subject,
                grade=grade,
                tlm_method=method,
                file_type=random.choice(["image", "document"]),
                file_url=None,
                original_filename=None,
                created_at=random_date(90),
            )
            db.add(post)
            db.flush()

            metric = Metric(
                post_id=post.id,
                view_count=random.randint(80, 800),
                like_count=random.randint(20, 120),
                download_count=random.randint(10, 80),
                comment_count=random.randint(5, 40),
            )
            db.add(metric)

        db.commit()
        print("Seed complete!")
        print(f"  Admin EMIS: {os.getenv('ADMIN_EMIS_ID', 'SCERT001')} | Password: {os.getenv('ADMIN_PASSWORD', 'scert@admin123')}")
        print(f"  Teacher EMIS IDs: 10000001 to 10000150 | Password: teacher@123")
        print(f"  Student EMIS: ST0000001 to ST0000200")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

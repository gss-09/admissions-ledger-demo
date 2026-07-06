"""Seed the DEMO database with rich, entirely FICTIONAL sample data.

This repository is a public example of a system that runs in production for an
educational institution serving 2,000-3,000 students (the production instance
tracks 1,400+ real applicants). Every name, phone number and rupee figure
created here is invented — no real data is used anywhere.

The seed exercises every feature of the app: the City -> Campus -> Course org
hierarchy, field + staff AGM teams with city bindings and rent, marketing execs
with the full cost breakdown (salary / general expenditure / incentive / gift)
and admission targets, ~1,500 applicants across every funnel stage with fees and
hostel choices, city-bound user accounts, and activity/login/password logs —
so the Home, Students, AGMs, Execs, Averages, Income and Expenditure screens all
have data to show.

Usage (point DATABASE_URL at an EMPTY Postgres database):
    DATABASE_URL="postgresql://..." python3 scripts/seed_demo.py

Demo credentials created:
    Public (shown on the login screen):
        viewer / Demo@1234          (read-only everywhere)
    Privileged (NEVER published — this is a public repo, so every account that
    can EDIT data gets a private password): set DEMO_ADMIN_PASSWORD (and
    optionally DEMO_ADMIN_USERNAME) in the environment before seeding, or the
    script generates a random password and prints it once at the end.
"""

import os
import random
import secrets
import sys
from datetime import timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import db, security       # noqa: E402
from app.schema import init_db     # noqa: E402
from app.config import STATUSES    # noqa: E402

random.seed(7)

# Read-only viewer — the ONLY credential published on the login screen/README.
VIEWER_PASSWORD = "Demo@1234"

# Accounts that can EDIT data (admin + editors) get a PRIVATE password: this
# repo is public, so a hard-coded value here would hand write access to anyone.
ADMIN_USERNAME = os.environ.get("DEMO_ADMIN_USERNAME", "ledger.admin").strip()
ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(12)

FIRST = [
    "Aadesh", "Aadhya", "Aakash", "Aakriti", "Aamani", "Aanya", "Aarav",
    "Aarohi", "Aarti", "Aaryan", "Abhay", "Abhijit", "Abhilash", "Abhinav",
    "Abhiram", "Abhishek", "Achyut", "Adarsh", "Adhira", "Aditi", "Aditya",
    "Advait", "Advika", "Agastya", "Ahalya", "Ahana", "Aishwarya", "Ajay",
    "Ajinkya", "Ajit", "Akanksha", "Akash", "Akhil", "Akhila", "Akshara",
    "Akshay", "Akshita", "Alekhya", "Alka", "Alok", "Amala", "Aman", "Amar",
    "Amarnath", "Ambika", "Amish", "Amisha", "Amit", "Amogh", "Amol",
    "Amrita", "Amrutha", "Amulya", "Anagha", "Anahita", "Anand", "Ananth",
    "Ananya", "Anika", "Aniket", "Anil", "Anila", "Anindita", "Anirudh",
    "Anish", "Anisha", "Anita", "Anitha", "Anjali", "Anjan", "Anjana",
    "Ankit", "Ankita", "Ankur", "Anmol", "Annapurna", "Anshika", "Antara",
    "Anup", "Anupama", "Anurag", "Anusha", "Anushka", "Anvi", "Apeksha",
    "Apoorva", "Aparna", "Aradhya", "Aravind", "Archana", "Archit", "Arjun",
    "Arnav", "Arpita", "Arun", "Aruna", "Arundhati", "Arvind", "Arya",
    "Asha", "Ashish", "Ashok", "Ashritha", "Ashutosh", "Ashwin", "Ashwini",
    "Asmita", "Atharv", "Atul", "Avani", "Avantika", "Avinash", "Ayaan",
    "Ayesha", "Ayush", "Ayushi",
    "Badri", "Balaji", "Balram", "Bhagya", "Bhagyashree", "Bhakti",
    "Bharat", "Bharath", "Bharathi", "Bhargav", "Bhargavi", "Bhavana",
    "Bhavani", "Bhavesh", "Bhavika", "Bhavin", "Bhavya", "Bhumika",
    "Bhuvan", "Bhuvana", "Bindu", "Brinda",
    "Chaitanya", "Chaitra", "Chakri", "Chandan", "Chandana", "Chandini",
    "Chandrika", "Charan", "Charitha", "Charu", "Charulatha", "Charvi",
    "Chetan", "Chetana", "Chinmay", "Chinmayi", "Chirag", "Chitra",
    "Daksh", "Damini", "Darshan", "Darshini", "Daya", "Deeksha",
    "Deekshith", "Deepa", "Deepak", "Deepali", "Deepika", "Deepthi", "Dev",
    "Devansh", "Devendra", "Devesh", "Devika", "Devraj", "Devyani",
    "Dhairya", "Dhananjay", "Dhanashree", "Dhanraj", "Dhanush", "Dhanya",
    "Dharani", "Dhriti", "Dhruthi", "Dhruv", "Digvijay", "Dilip", "Dinesh",
    "Dipti", "Disha", "Divakar", "Divij", "Divya", "Divyansh", "Diya",
    "Drishti", "Durgesh",
    "Ekansh", "Ekta", "Esha", "Eshan", "Eshita", "Eshwar", "Falguni",
    "Gagan", "Gargi", "Gaurang", "Gauri", "Gautham", "Gautami", "Gayathri",
    "Geetha", "Girija", "Girish", "Gita", "Gitanjali", "Gokul", "Gopal",
    "Gopika", "Gourav", "Govind", "Gowri", "Greeshma", "Gunjan", "Guru",
    "Hamsini", "Hansika", "Hari", "Harika", "Harini", "Haripriya",
    "Harish", "Haritha", "Harsha", "Harshad", "Harshavardhan", "Harshini",
    "Harshit", "Harshita", "Hasini", "Hema", "Hemalatha", "Hemang",
    "Hemanth", "Himaja", "Himani", "Himanshu", "Hitesh", "Hrithik",
    "Ila", "Inchara", "Indira", "Indrajit", "Indu", "Ipsita", "Ira",
    "Isha", "Ishaan", "Ishani", "Ishika", "Ishita",
    "Jagadish", "Jagruti", "Jahnavi", "Jai", "Jaideep", "Janaki", "Janani",
    "Jaswanth", "Jatin", "Jaya", "Jayant", "Jayanthi", "Jayasree",
    "Jayesh", "Jeevan", "Jhansi", "Jignesh", "Jitendra", "Jyothi",
    "Jyotsna",
    "Kadambari", "Kailash", "Kajal", "Kalpana", "Kalyan", "Kalyani",
    "Kamakshi", "Kamal", "Kamala", "Kamini", "Kanaka", "Kanika", "Kanishk",
    "Kapil", "Karan", "Karishma", "Karthik", "Karthika", "Kartik",
    "Kartikeya", "Karuna", "Kashish", "Kasturi", "Kaushal", "Kaushik",
    "Kavana", "Kavin", "Kavita", "Kavitha", "Kavya", "Kedar", "Keerthana",
    "Keerthi", "Keshav", "Ketaki", "Ketan", "Keya", "Khushi", "Kinjal",
    "Kiran", "Kirti", "Kishan", "Kishore", "Komal", "Kranthi", "Krish",
    "Krishnaveni", "Kriti", "Kruthika", "Kshitij", "Kumud", "Kunal",
    "Kushal",
    "Lahari", "Lakshit", "Lakshman", "Lakshmi", "Lalita", "Lalith",
    "Lalitha", "Lasya", "Latha", "Lavanya", "Laxmi", "Laya", "Leela",
    "Leena", "Likhitha", "Likith", "Lipika", "Lohith", "Lokesh",
    "Madhav", "Madhavi", "Madhu", "Madhulika", "Madhumita", "Madhur",
    "Madhuri", "Mahati", "Mahendra", "Mahi", "Mahima", "Mahitha",
    "Malavika", "Malini", "Mallika", "Mamata", "Manas", "Manasa", "Manav",
    "Mangala", "Manideep", "Manish", "Manisha", "Manjari", "Manju",
    "Manoj", "Mansi", "Manvitha", "Maya", "Mayank", "Mayur", "Medha",
    "Meena", "Meenakshi", "Meera", "Megha", "Meghana", "Menaka", "Mihir",
    "Milan", "Mitali", "Mitesh", "Mithra", "Mithun", "Mohit", "Mokshith",
    "Monika", "Mounika", "Mridula", "Mrunal", "Mukesh", "Mukta", "Mukund",
    "Murali", "Mythili", "Mythri",
    "Nachiket", "Nagesh", "Naina", "Nakshatra", "Nakul", "Nalin", "Naman",
    "Namitha", "Namratha", "Nandan", "Nandini", "Nandita", "Narendra",
    "Naresh", "Naveen", "Naveena", "Navya", "Nayan", "Nayana", "Neel",
    "Neelam", "Neelima", "Neeraj", "Neeraja", "Neha", "Nehal", "Netra",
    "Nidhi", "Niharika", "Nihal", "Nikhil", "Nikhila", "Nikitha", "Nikunj",
    "Nilesh", "Nimisha", "Nipun", "Niranjan", "Nirav", "Nirmala",
    "Nischal", "Nisha", "Nishad", "Nishant", "Nishitha", "Nithin",
    "Nithya", "Nitin", "Nivedita", "Niyati", "Nutan",
    "Ojas", "Om", "Omkar",
    "Padma", "Padmaja", "Padmini", "Palak", "Palash", "Pallavi", "Pankaj",
    "Parag", "Paras", "Paridhi", "Parth", "Parul", "Parvathi", "Pavan",
    "Pavani", "Pavithra", "Payal", "Phani", "Phanindra", "Piyush", "Pooja",
    "Poojitha", "Poorna", "Poornima", "Prabha", "Prabhat", "Prachi",
    "Pradeep", "Pradnya", "Pragathi", "Pragna", "Prajwal", "Pramod",
    "Pranathi", "Pranav", "Pranay", "Praneeth", "Pranita", "Pranjal",
    "Pranshu", "Prasanna", "Prasanth", "Pratap", "Pratibha", "Pratik",
    "Pratima", "Pratyush", "Praveen", "Praveena", "Pravalika", "Preetham",
    "Preethi", "Preksha", "Prem", "Prerana", "Priya", "Priyanka",
    "Priyansh", "Prithvi", "Puneet", "Pushkar", "Pushpa",
    "Rachana", "Rachit", "Radha", "Radhika", "Ragini", "Raghavendra",
    "Rahul", "Raj", "Rajani", "Rajat", "Rajeshwari", "Rajitha", "Rajiv",
    "Rakesh", "Rakshit", "Rakshita", "Ram", "Ramya", "Rani", "Ranjan",
    "Ranjani", "Ranjith", "Ranveer", "Rasika", "Rashi", "Rashmi", "Ratan",
    "Ravali", "Raveena", "Ravi", "Rekha", "Renu", "Renuka", "Reshma",
    "Revanth", "Revathi", "Richa", "Riddhi", "Ridhima", "Rishabh",
    "Rishi", "Rishika", "Ritesh", "Rithik", "Ritika", "Ritu", "Ritvik",
    "Riya", "Rohan", "Rohini", "Rohit", "Roshan", "Roshni", "Rounak",
    "Ruchi", "Ruchira", "Rudra", "Rukmini", "Rupa", "Rupali", "Rutuja",
    "Saanvi", "Sachin", "Sadhana", "Sagar", "Sahana", "Sahasra", "Sahil",
    "Sahithi", "Sai", "Saket", "Sakshi", "Saloni", "Samaira", "Samatha",
    "Sameer", "Samhita", "Samiksha", "Sampada", "Samyuktha", "Sanchit",
    "Sandeep", "Sandhya", "Sangeetha", "Sanika", "Sanjana", "Sanjay",
    "Sanket", "Santosh", "Sarala", "Saraswati", "Sarayu", "Sarika",
    "Sarthak", "Sarvesh", "Sasank", "Sathvik", "Sathwika", "Satish",
    "Saurabh", "Savita", "Savitha", "Shailaja", "Shailesh", "Shalini",
    "Shambhavi", "Shanmukh", "Shantanu", "Shanti", "Sharad", "Sharada",
    "Sharan", "Sharanya", "Sharath", "Sharvani", "Shashank", "Shashi",
    "Shaunak", "Sheela", "Shefali", "Shilpa", "Shishir", "Shiva",
    "Shivam", "Shivangi", "Shivani", "Shivansh", "Shobha", "Shraddha",
    "Shravan", "Shreya", "Shreyansh", "Shreyas", "Shristi", "Shruthi",
    "Shruti", "Shubha", "Shubham", "Shubhangi", "Shyam", "Siddharth",
    "Siddhesh", "Siddhi", "Simran", "Sindhu", "Siri", "Sirisha", "Sita",
    "Sitara", "Smita", "Smitha", "Smriti", "Sneha", "Snehal", "Snigdha",
    "Soham", "Sohan", "Somesh", "Sonal", "Sonali", "Sonam", "Sonia",
    "Sourav", "Spandana", "Sravani", "Sravya", "Sreeja", "Sreekar",
    "Sreenidhi", "Sridevi", "Sridhar", "Srihari", "Srija", "Srikanth",
    "Srilatha", "Srivatsa", "Srividya", "Subhash", "Sucharita",
    "Sudarshan", "Sudeep", "Sudha", "Suhani", "Suhas", "Suhasini",
    "Sujal", "Sujatha", "Sujith", "Sukanya", "Sukriti", "Sukumar", "Suma",
    "Suman", "Sumanth", "Sumedh", "Sumedha", "Sumit", "Sunaina", "Sundar",
    "Sunidhi", "Sunil", "Sunita", "Sunitha", "Suparna", "Supriya",
    "Surabhi", "Suraj", "Surekha", "Surya", "Sushant", "Sushma",
    "Susmitha", "Suvarna", "Suyash", "Swapna", "Swapnil", "Swara",
    "Swaroop", "Swathi", "Swati", "Swetha", "Syamala",
    "Tanay", "Tanaya", "Tanish", "Tanisha", "Tanmay", "Tanuja",
    "Tanushree", "Tanvi", "Tara", "Tarun", "Taruni", "Tejal", "Tejas",
    "Tejaswi", "Tilak", "Trisha", "Triveni", "Trupti", "Tulasi", "Tushar",
    "Uday", "Ujjwal", "Ujwala", "Uma", "Umesh", "Urmila", "Urvashi",
    "Usha", "Utkarsh", "Uttam",
    "Vaibhav", "Vaidehi", "Vaishali", "Vaishnavi", "Vamsi", "Vanaja",
    "Vandana", "Vani", "Vanshika", "Varalakshmi", "Varsha", "Varun",
    "Vasanth", "Vasavi", "Vasudha", "Vasundhara", "Vatsal", "Vedansh",
    "Vedant", "Vedika", "Veena", "Vennela", "Venu", "Vibha", "Vidhi",
    "Vidya", "Vignesh", "Vihaan", "Vijay", "Vikas", "Vikram", "Vikrant",
    "Vimal", "Vinay", "Vinaya", "Vineet", "Vineetha", "Vinod", "Vinutha",
    "Vipin", "Vipul", "Viraj", "Vishaka", "Vishal", "Vishnu", "Vishruth",
    "Vishwa", "Vishwas", "Vismaya", "Vivek", "Vrinda",
    "Yamini", "Yasaswi", "Yash", "Yashika", "Yashoda", "Yashwanth",
    "Yatin", "Yogesh", "Yogita", "Yuktha", "Yuvan", "Yuvraj"]
# International pool — paired only with INTL_LAST so every student's name
# stays culturally coherent.
INTL_FIRST = [
    "Aaron", "Abigail", "Adam", "Adrian", "Ahmed", "Aiden", "Aisha",
    "Alan", "Albert", "Alex", "Alexa", "Alexander", "Alexis", "Alice",
    "Alicia", "Allison", "Alyssa", "Amanda", "Amber", "Amelia", "Amina",
    "Amy", "Andre", "Andrea", "Andrew", "Angela", "Anna", "Anthony",
    "Antonio", "April", "Ariana", "Arthur", "Ashley", "Aubrey", "Audrey",
    "Austin", "Autumn", "Ava", "Bailey", "Beatrice", "Bella", "Benjamin",
    "Bianca", "Blake", "Brandon", "Brenda", "Brian", "Brianna", "Brooke",
    "Caleb", "Cameron", "Camila", "Carla", "Carlos", "Carmen", "Caroline",
    "Carter", "Cassandra", "Catherine", "Cecilia", "Charles", "Charlotte",
    "Chase", "Chelsea", "Chloe", "Christian", "Christina", "Christopher",
    "Claire", "Clara", "Cody", "Cole", "Colin", "Connor", "Courtney",
    "Crystal", "Cynthia", "Daisy", "Dakota", "Damian", "Daniel",
    "Daniela", "David", "Dean", "Declan", "Derek", "Diana", "Diego",
    "Dominic", "Dylan", "Edward", "Elena", "Eli", "Elias", "Elijah",
    "Elif", "Elizabeth", "Ella", "Ellie", "Emily", "Emma", "Emre",
    "Eric", "Erica", "Erin", "Ethan", "Eva", "Evan", "Evelyn", "Ezra",
    "Faith", "Fatima", "Felipe", "Felix", "Fiona", "Francesca", "Frank",
    "Gabriel", "Gabriela", "Gavin", "George", "Georgia", "Gianna",
    "Giovanni", "Giulia", "Grace", "Grant", "Gregory", "Hailey", "Hana",
    "Hannah", "Harper", "Harry", "Hassan", "Hazel", "Heather", "Hector",
    "Helen", "Henry", "Hiroshi", "Holly", "Hope", "Hunter", "Ian",
    "Ines", "Ingrid", "Irene", "Isaac", "Isabel", "Isaiah", "Ivan",
    "Ivy", "Jack", "Jacob", "Jade", "James", "Jasmine", "Jason",
    "Jayden", "Jeffrey", "Jenna", "Jennifer", "Jeremy", "Jesse",
    "Jessica", "Joanna", "Joel", "John", "Jonah", "Jonathan", "Jordan",
    "Jorge", "Jose", "Joseph", "Joshua", "Juan", "Julia", "Julian",
    "Juliana", "Justin", "Kaitlyn", "Kara", "Kate", "Kayla", "Keith",
    "Kelly", "Kelsey", "Kenji", "Kevin", "Khalid", "Kimberly", "Kyle",
    "Kylie", "Landon", "Lars", "Laura", "Lauren", "Layla", "Leah",
    "Leila", "Leo", "Leon", "Levi", "Liam", "Lillian", "Lily", "Lisa",
    "Logan", "Lorenzo", "Lucas", "Lucia", "Lucy", "Luis", "Lukas",
    "Luke", "Luna", "Lydia", "Mackenzie", "Madeline", "Madison", "Malik",
    "Marco", "Marcus", "Margaret", "Maria", "Mariah", "Mario", "Marissa",
    "Mark", "Marta", "Martin", "Mary", "Mason", "Mateo", "Matthew",
    "Megan", "Mei", "Melanie", "Melissa", "Mia", "Michael", "Michelle",
    "Miguel", "Miles", "Miriam", "Molly", "Monica", "Morgan", "Nadia",
    "Natalie", "Natasha", "Nathan", "Nicholas", "Nicole", "Nina", "Noah",
    "Nolan", "Nora", "Oliver", "Olivia", "Omar", "Oscar", "Owen",
    "Paige", "Patrick", "Paul", "Paula", "Paulo", "Pedro", "Penelope",
    "Peter", "Petra", "Philip", "Phoebe", "Quinn", "Rachel", "Rafael",
    "Rania", "Raymond", "Rebecca", "Regina", "Renata", "Ricardo",
    "Richard", "Riley", "Robert", "Rosa", "Rose", "Ruby", "Ruth",
    "Ryan", "Sabrina", "Sadie", "Salma", "Sam", "Samantha", "Samuel",
    "Sandra", "Santiago", "Sara", "Savannah", "Scarlett", "Scott",
    "Sean", "Sebastian", "Serena", "Shane", "Sierra", "Simon", "Sofia",
    "Sophie", "Spencer", "Stefan", "Stella", "Stephanie", "Steven",
    "Summer", "Sven", "Sydney", "Taylor", "Teresa", "Theodore", "Thomas",
    "Timothy", "Tobias", "Tomas", "Travis", "Trevor", "Tristan", "Tyler",
    "Valentina", "Valerie", "Vanessa", "Veronica", "Victor", "Victoria",
    "Vincent", "Violet", "Vivian", "Wendy", "Wesley", "William",
    "Willow", "Wyatt", "Yara", "Yasmin", "Yuki", "Yusuf", "Zachary",
    "Zara", "Zeynep", "Zoe"]
LAST = ["Rao", "Reddy", "Sharma", "Varma", "Naidu", "Iyer", "Menon", "Gupta",
        "Patel", "Chowdary", "Kumar", "Prasad", "Murthy", "Sastry", "Pillai",
        "Nair", "Joshi", "Kulkarni", "Deshmukh", "Bhat",
        "Agarwal", "Banerjee", "Bhandari", "Chauhan", "Desai", "Dutta",
        "Ghosh", "Hegde", "Jain", "Kamath", "Kapoor", "Khanna", "Mishra",
        "Pandey", "Rathore", "Saxena", "Shetty", "Sinha", "Tripathi",
        "Trivedi", "Verma",
        "Acharya", "Arora", "Basu", "Bhagat", "Bhargava", "Bhatt", "Bisht",
        "Chatterjee", "Chawla", "Chopra", "Das", "Dave", "Dixit", "Dubey",
        "Gaikwad", "Garg", "Goel", "Gokhale", "Goswami", "Gowda", "Grover",
        "Iyengar", "Jadhav", "Jaiswal", "Jha", "Kadam", "Kale", "Kashyap",
        "Khatri", "Kohli", "Krishnan", "Mahajan", "Malhotra", "Mathur",
        "Mehta", "Mittal", "Mukherjee", "Nambiar", "Nanda", "Oberoi",
        "Pal", "Parikh", "Pathak", "Patil", "Pawar", "Puri", "Raghavan",
        "Rajan", "Raman", "Rana", "Rawat", "Roy", "Sahu", "Sawant", "Sen",
        "Seth", "Shah", "Shukla", "Solanki", "Srinivasan", "Subramaniam",
        "Sundaram", "Swamy", "Tandon", "Thakur", "Tiwari", "Vaidya",
        "Wadhwa", "Yadav",
        "Ahuja", "Awasthi", "Bajpai", "Balan", "Bansal", "Bedi", "Behera",
        "Bhalla", "Bhardwaj", "Bhasin", "Bhatia", "Bhatnagar",
        "Bhattacharya", "Bhosale", "Borkar", "Chandran", "Chaturvedi",
        "Chhabra", "Dalal", "Deshpande", "Dhar", "Dhawan", "Gandhi",
        "Ganesan", "Gill", "Godbole", "Gulati", "Handa", "Inamdar",
        "Kakkar", "Kalra", "Kannan", "Kapadia", "Karnik", "Khandelwal",
        "Khare", "Khosla", "Kothari", "Lal", "Luthra", "Madan", "Mani",
        "Marathe", "Mohanty", "Mudaliar", "Munshi", "Nagarajan", "Naik",
        "Nayak", "Padmanabhan", "Pai", "Panda", "Panicker", "Parekh",
        "Phadke", "Prabhu", "Pradhan", "Raheja", "Rajagopal",
        "Ramachandran", "Sabharwal", "Sachdeva", "Salvi", "Samant",
        "Sampath", "Sanyal", "Sarkar", "Sathe", "Sehgal", "Shenoy", "Sood",
        "Soni", "Srivastava", "Suri", "Talwar", "Tambe", "Thakkar",
        "Uppal", "Vaswani", "Venkatesan", "Vohra", "Walia"]
# Andhra/Telangana-style village surnames, composed from real stem+suffix
# morphology (Chintalapati, Kondaveeti, Mullapudi, ...). This yields ~1,200
# extra distinct surnames so that, with _LAST_CAP below, virtually no two
# students look like they come from the same family.
_SUR_STEM = ["Adda", "Alla", "Amba", "Anka", "Bada", "Banda", "Bhima",
             "Bikka", "Bomma", "Bukka", "Challa", "Chava", "Chikka",
             "Chilla", "Chinta", "Chitta", "Danda", "Dasa", "Devara",
             "Edara", "Ella", "Gaja", "Ganta", "Garla", "Gudi", "Gulla",
             "Gutta", "Jalla", "Jonna", "Kalva", "Kanda", "Kanna", "Karra",
             "Katta", "Kola", "Komma", "Konda", "Kota", "Kunda", "Madda",
             "Malla", "Manda", "Metta", "Mulla", "Nakka", "Nalla", "Nara",
             "Neela", "Palla", "Peddi", "Penta", "Pinna", "Pola", "Ponna",
             "Putta", "Singa", "Sura", "Talla", "Thota", "Vanka", "Vasa",
             "Vella", "Vemula", "Venna", "Yella"]
_SUR_SUFFIX = ["pati", "pudi", "palli", "vada", "varapu", "veeti", "lanka",
               "gadda", "prolu", "palem", "padu", "gunta", "kunta", "konda",
               "kota", "giri", "metla", "gudem", "cherla"]
LAST += [s + x for s in _SUR_STEM for x in _SUR_SUFFIX if s.lower() != x]
LAST = list(dict.fromkeys(LAST))
INTL_LAST = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Taylor", "Moore", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall",
    "Rivera", "Campbell", "Mitchell", "Roberts", "Gomez", "Phillips",
    "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins",
    "Reyes", "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers",
    "Gutierrez", "Ortiz", "Cooper", "Peterson", "Reed", "Howard", "Ramos",
    "Cox", "Ward", "Richardson", "Watson", "Brooks", "Chavez", "Wood",
    "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes", "Price", "Alvarez",
    "Castillo", "Sanders", "Myers", "Foster", "Jimenez", "Powell",
    "Jenkins", "Perry", "Sullivan", "Bell", "Coleman", "Butler",
    "Henderson", "Barnes", "Fisher", "Vasquez", "Simmons", "Romero",
    "Patterson", "Hamilton", "Graham", "Reynolds", "Griffin", "Wallace",
    "Moreno", "West", "Hayes", "Bryant", "Herrera", "Gibson", "Ellis",
    "Tran", "Medina", "Aguilar", "Stevens", "Murray", "Ford", "Castro",
    "Marshall", "Owens", "Harrison", "Fernandez", "McDonald", "Woods",
    "Washington", "Kennedy", "Wells", "Vargas", "Freeman", "Webb",
    "Tucker", "Guzman", "Burns", "Crawford", "Olson", "Simpson",
    "Porter", "Gordon", "Mendez", "Silva", "Shaw", "Snyder", "Dixon",
    "Munoz", "Hicks", "Holmes", "Palmer", "Wagner", "Black", "Robertson",
    "Boyd", "Stone", "Salazar", "Fox", "Warren", "Mills", "Meyer",
    "Rice", "Schmidt", "Garza", "Daniels", "Ferguson", "Nichols",
    "Stephens", "Soto", "Weaver", "Gardner", "Payne", "Dunn", "Hawkins",
    "Arnold", "Pierce", "Hansen", "Peters", "Santos", "Hart", "Bradley",
    "Knight", "Elliott", "Cunningham", "Duncan", "Armstrong", "Hudson",
    "Carroll", "Lane", "Andrews", "Alvarado", "Delgado", "Berry",
    "Perkins", "Hoffman", "Johnston", "Matthews", "Pena", "Richards",
    "Contreras", "Willis", "Carpenter", "Lawrence", "Sandoval",
    "Guerrero", "Chapman", "Rios", "Estrada", "Ortega", "Watkins",
    "Greene", "Nunez", "Wheeler", "Valdez", "Burke", "Larson",
    "Maldonado", "Morrison", "Franklin", "Carlson", "Dominguez", "Carr",
    "Lawson", "Jacobs", "Lynch", "Vega", "Bishop", "Montgomery",
    "Jensen", "Harvey", "Williamson", "Gilbert", "Sims", "Espinoza",
    "Howell", "Wong", "Reid", "Hanson", "McCoy", "Garrett", "Burton",
    "Fuller", "Weber", "Welch", "Rojas", "Marquez", "Fields", "Little",
    "Banks", "Padilla", "Walsh", "Bowman", "Schultz", "Fowler", "Mejia",
    "Davidson", "Acosta", "Brewer", "Holland", "Juarez", "Newman",
    "Pearson", "Curtis", "Cortez", "Douglas", "Schneider", "Barrett",
    "Navarro", "Figueroa", "Keller", "Avila", "Wade", "Molina",
    "Stanley", "Hopkins", "Barnett", "Bates", "Chambers", "Caldwell",
    "Beck", "Lambert", "Miranda", "Byrd", "Craig", "Ayala", "Lowe",
    "Frazier", "Powers", "Neal", "Leonard", "Carrillo", "Sutton",
    "Fleming", "Rhodes", "Shelton", "Schwartz", "Norris", "Jennings",
    "Watts", "Duran", "Walters", "Cohen", "McDaniel", "Moran", "Steele",
    "Vaughn", "Becker", "Holt", "Barker", "Terry", "Hale",
    "Mueller", "Fischer", "Schulz", "Zimmermann", "Braun", "Kruger",
    "Hartmann", "Lange", "Werner", "Krause", "Meier", "Lehmann",
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano",
    "Colombo", "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti",
    "Mancini", "Costa", "Giordano", "Rizzo", "Lombardi", "Moretti",
    "Dubois", "Bernard", "Durand", "Petit", "Leroy", "Moreau",
    "Laurent", "Lefebvre", "Michel", "Garnier", "Roux", "Fournier",
    "Girard", "Bonnet", "Kowalski", "Nowak", "Kaminski", "Lewandowski",
    "Zielinski", "Andersson", "Johansson", "Karlsson", "Nilsson",
    "Eriksson", "Larsson", "Olsen", "Pedersen", "Nielsen", "Berg",
    "Haugen", "Bakker", "Visser", "Smit", "Mulder", "Bos", "Vos",
    "Hendriks", "Dekker", "Brouwer", "Dijkstra", "Kuiper", "Kramer",
    "Papadopoulos", "Nikolaou", "Georgiou", "Dimitriou", "Yilmaz",
    "Kaya", "Demir", "Celik", "Sahin", "Ozturk", "Aydin", "Aksoy",
    "Ivanov", "Petrov", "Sokolov", "Popov", "Volkov", "Smirnov",
    "Kuznetsov", "Novikov", "Morozov", "Fedorov", "Mikhailov", "Kozlov",
    "Lebedev", "Semenov", "Pavlov", "Orlov", "Makarov", "Andreev",
    "Zaitsev", "Borisov", "Yakovlev", "Romanov",
    "Tanaka", "Suzuki", "Takahashi", "Watanabe", "Ito", "Yamamoto",
    "Nakamura", "Kobayashi", "Kato", "Yoshida", "Yamada", "Sasaki",
    "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Saito",
    "Mori", "Abe", "Ikeda", "Hashimoto", "Ogawa", "Ishikawa", "Maeda",
    "Fujita", "Okada", "Hasegawa", "Murakami", "Kondo", "Ishii",
    "Sakamoto", "Endo", "Aoki", "Fujii", "Nishimura", "Fukuda", "Miura",
    "Takeuchi", "Nakajima", "Okamoto", "Matsuda", "Nakagawa", "Harada",
    "Ono", "Tamura", "Takeda", "Ueda", "Kim", "Park", "Choi", "Jung",
    "Kang", "Cho", "Yoon", "Jang", "Lim", "Han", "Shin", "Seo", "Kwon",
    "Song", "Hong", "Yoo", "Bae", "Nam", "Moon", "Oh", "Chung",
    "Zhang", "Liu", "Chen", "Huang", "Zhao", "Wu", "Zhou", "Xu", "Sun",
    "Zhu", "Hu", "Guo", "Gao", "Lin", "Luo", "Zheng", "Liang", "Xie",
    "Tang", "Deng", "Feng", "Peng", "Cao", "Zeng", "Xiao", "Tian",
    "Dong", "Pan", "Yuan", "Cai", "Jiang", "Yu", "Du", "Ye", "Cheng",
    "Wei", "Su", "Ding", "Ren", "Yao", "Fang", "Shen", "Jin", "Qin",
    "Hou", "Pham", "Hoang", "Phan", "Vu", "Vo", "Dang", "Bui", "Do",
    "Ho", "Duong", "Ly", "Wang", "Li",
    "Hussein", "Ibrahim", "Mahmoud", "Rahman", "Aziz", "Karim", "Farah",
    "Nasser", "Saleh", "Khalil", "Mansour", "Mustafa", "Qureshi",
    "Sheikh", "Siddiqui", "Ansari", "Mirza", "Baig", "Okafor", "Okoro",
    "Eze", "Nwosu", "Adeyemi", "Adebayo", "Okonkwo", "Chukwu", "Obi",
    "Mensah", "Boateng", "Owusu", "Asante", "Osei", "Appiah", "Diallo",
    "Toure", "Kone", "Traore", "Keita", "Cisse", "Ndiaye", "Diop",
    "Sow", "Fall", "Sarr", "Mwangi", "Kamau", "Njoroge", "Otieno",
    "Ochieng", "Abebe", "Bekele", "Tesfaye", "Girma", "Haile",
    "Dlamini", "Nkosi", "Ndlovu", "Khumalo", "Mokoena", "Botha",
    "Oliveira", "Souza", "Pereira", "Almeida", "Ferreira", "Ribeiro",
    "Carvalho", "Gomes", "Barbosa", "Cardoso", "Teixeira", "Moraes",
    "Fonseca", "Machado", "Araujo", "Melo", "Nogueira", "Pinto",
    "Correia", "Cunha", "Freitas", "Batista", "Rocha", "Azevedo",
    "Barros", "Duarte", "Mendes", "Monteiro", "Moura", "Neves", "Nunes",
    "Pires", "Queiroz", "Tavares", "Vieira"]
INTL_LAST = list(dict.fromkeys(INTL_LAST))
FATHER_FIRST = ["Ramesh", "Suresh", "Mahesh", "Rajesh", "Ganesh", "Prakash",
                "Srinivas", "Venkatesh", "Mohan", "Krishna", "Ravindra",
                "Narayana", "Sudhakar", "Chandra", "Bhaskar",
                "Anjaneyulu", "Ashok", "Damodar", "Eswar", "Hanumantha",
                "Jagan", "Koteswara", "Madhava", "Nagendra", "Narasimha",
                "Purushotham", "Raghava", "Raghu", "Rajendra", "Ranga",
                "Sambasiva", "Sankar", "Satyanarayana", "Seshagiri",
                "Someswara", "Subrahmanyam", "Sudheer", "Tirupathi",
                "Vasudeva", "Veerabhadra"]
INTL_FATHER = ["Robert", "James", "David", "Michael", "William", "Richard",
               "Carlos", "Miguel", "Antonio", "Giovanni", "Klaus", "Stefan",
               "Andrei", "Dmitri", "Kenji", "Takashi", "Jun", "Wei",
               "Ahmed", "Omar", "Hassan", "Ibrahim", "Kwame", "Emeka",
               "Pedro", "Rafael", "Thomas", "Peter", "Henrik", "Lars"]

# Students draw from one of two culturally-coherent (first, last, father)
# pools. Full names are unique and never collide with a seeded staff name.
# Hard per-name caps keep the roster realistic: a first name appears at most
# 3 times, and a surname at most twice (one family = at most 1-2 siblings).
FIRST = list(dict.fromkeys(FIRST))
INTL_FIRST = list(dict.fromkeys(INTL_FIRST))
_POOLS = ((FIRST, LAST, FATHER_FIRST),
          (INTL_FIRST, INTL_LAST, INTL_FATHER))
_INDIAN_SHARE = 0.6
_USED_NAMES = {"Meghana Kulkarni", "Sameer Joshi", "Anita Bhat",
               "Arjun Mehta", "Bhargav Raju", "Chitra Nair",
               "Dinesh Rawal"}
_FIRST_USED = {}
_LAST_USED = {}
_FIRST_CAP = 3
_LAST_CAP = 2

if ((len(FIRST) + len(INTL_FIRST)) * _FIRST_CAP < 1700
        or (len(LAST) + len(INTL_LAST)) * _LAST_CAP < 1700):
    sys.exit("seed_demo: name pools too small for the student count.")


def unique_name():
    """A unique (student full name, father full name) pair."""
    while True:
        firsts, lasts, fathers = (
            _POOLS[0] if random.random() < _INDIAN_SHARE else _POOLS[1])
        first = random.choice(firsts)
        last = random.choice(lasts)
        full = f"{first} {last}"
        if (first == last or full in _USED_NAMES
                or _FIRST_USED.get(first, 0) >= _FIRST_CAP
                or _LAST_USED.get(last, 0) >= _LAST_CAP):
            continue
        _USED_NAMES.add(full)
        _FIRST_USED[first] = _FIRST_USED.get(first, 0) + 1
        _LAST_USED[last] = _LAST_USED.get(last, 0) + 1
        return full, f"{random.choice(fathers)} {last}"

# The fictional recruiting org.
CITIES = {
    "NORTHVALE": ["NORTHVALE DS", "NORTHVALE HOSTEL"],
    "EASTPORT":  ["EASTPORT DS"],
    "WESTBROOK": ["WESTBROOK DS"],
}
CAMPUS_COURSES = {
    "NORTHVALE DS":     ["MPC", "BIPC", "MEC", "CEC"],
    "NORTHVALE HOSTEL": ["MPC", "BIPC"],
    "EASTPORT DS":      ["MPC", "BIPC"],
    "WESTBROOK DS":     ["MPC"],
}
# AGM teams: (name, city, is_field, rent). Field teams recruit on the ground and
# carry premises rent; the staff team's salaries are not an admission cost.
AGMS = [
    ("ARJUN MEHTA",  "NORTHVALE", 1, 45000),
    ("BHARGAV RAJU", "NORTHVALE", 1, 38000),
    ("CHITRA NAIR",  "EASTPORT",  1, 30000),
    ("DINESH RAWAL", "WESTBROOK", 1, 25000),
    ("CAMPUS STAFF", "NORTHVALE", 0, 0),
]
EXECS_PER_AGM = (3, 5)


def fake_phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


def day(offset):
    return (db.now_dt() - timedelta(days=offset)).strftime("%Y-%m-%d")


def main():
    if not os.environ.get("DATABASE_URL"):
        sys.exit("Set DATABASE_URL to an EMPTY demo Postgres database first.")

    if security.password_too_short(ADMIN_PASSWORD):
        sys.exit("DEMO_ADMIN_PASSWORD must be at least "
                 f"{security.MIN_PASSWORD_LEN} characters.")
    if not ADMIN_USERNAME or ADMIN_USERNAME == "viewer":
        sys.exit("DEMO_ADMIN_USERNAME must be a non-empty name other than 'viewer'.")

    print("Initialising schema ...")
    init_db()
    viewer_hash = security.hash_password(VIEWER_PASSWORD)
    admin_hash = security.hash_password(ADMIN_PASSWORD)

    with db.connect() as conn:
        seed(conn, viewer_hash, admin_hash)
        conn.commit()

    print("Demo data seeded.")
    print(f"  Public sign-in (read-only): viewer / {VIEWER_PASSWORD}")
    print(f"  Administrator (KEEP PRIVATE): {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print("  (editor / editor.northvale share the administrator password)")


def seed(conn, viewer_hash, admin_hash):
    now = db.now()

    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('demo_notice', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("EXAMPLE DATABASE — every record here is fictional sample data. "
         "This public repository mirrors a system already running in production "
         "for an educational institution with 2,000-3,000 students.",))

    # ---- Cities, campuses, courses (init_db seeded some; make sure of all) --
    city_ids, campus_ids = {}, {}
    for city, campuses in CITIES.items():
        row = conn.execute("SELECT id FROM cities WHERE name = ?", (city,)).fetchone()
        city_ids[city] = row["id"] if row else db.insert(
            conn, "INSERT INTO cities (name, created_at) VALUES (?, ?)", (city, now))
        for campus in campuses:
            row = conn.execute("SELECT id FROM campuses WHERE name = ?",
                               (campus,)).fetchone()
            cid = row["id"] if row else db.insert(
                conn, "INSERT INTO campuses (name, created_at) VALUES (?, ?)",
                (campus, now))
            campus_ids[campus] = cid
            conn.execute("UPDATE campuses SET city_id = ? WHERE id = ?",
                         (city_ids[city], cid))
    for campus, courses in CAMPUS_COURSES.items():
        for course in courses:
            conn.execute(
                "INSERT INTO courses (campus_id, name, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT (campus_id, name) DO NOTHING",
                (campus_ids[campus], course, now))

    # ---- Users: admin + editor + city-bound editor + viewer -----------------
    # Rename the first-run 'admin' account and give every edit-capable account
    # the private password; only the read-only viewer gets the published one.
    conn.execute("UPDATE users SET username = ?, password_hash = ? "
                 "WHERE username IN ('admin', ?)",
                 (ADMIN_USERNAME, admin_hash, ADMIN_USERNAME))
    users = [("editor", "Meghana Kulkarni", "editor", admin_hash),
             ("editor.northvale", "Sameer Joshi", "editor", admin_hash),
             ("viewer", "Anita Bhat", "viewer", viewer_hash)]
    for username, full, role, phash in users:
        if not conn.execute("SELECT 1 FROM users WHERE username = ?",
                            (username,)).fetchone():
            conn.execute(
                "INSERT INTO users (username, full_name, role, password_hash, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (username, full, role, phash, now))
        else:
            conn.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                         (phash, username))
    bound = conn.execute("SELECT id FROM users WHERE username = 'editor.northvale'"
                         ).fetchone()
    conn.execute(
        "INSERT INTO user_cities (user_id, city_id) VALUES (?, ?) "
        "ON CONFLICT (user_id, city_id) DO NOTHING",
        (bound["id"], city_ids["NORTHVALE"]))

    admin = conn.execute("SELECT id FROM users WHERE username = ?",
                         (ADMIN_USERNAME,)).fetchone()
    conn.execute(
        "INSERT INTO password_changes (target_user_id, target_name, "
        "target_username, actor_user_id, actor_name, actor_username, kind, "
        "created_at) VALUES (?, 'Anita Bhat', 'viewer', ?, 'Administrator', "
        "?, 'reset', ?)", (bound["id"], admin["id"], ADMIN_USERNAME, now))

    # ---- AGM teams + marketing execs (full cost breakdown) ------------------
    agm_execs = {}     # agm name -> [exec names]
    for name, city, is_field, rent in AGMS:
        row = conn.execute("SELECT id FROM agms WHERE name = ?", (name,)).fetchone()
        agm_id = row["id"] if row else db.insert(
            conn, "INSERT INTO agms (name, created_at) VALUES (?, ?)", (name, now))
        conn.execute("UPDATE agms SET city_id = ?, is_field = ?, rent = ? "
                     "WHERE id = ?", (city_ids[city], is_field, rent, agm_id))
        agm_execs[name] = []
        for _ in range(random.randint(*EXECS_PER_AGM)):
            ename = unique_name()[0].upper()
            gen_exp = random.randrange(3000, 9000, 500)
            incentive = random.randrange(0, 12000, 1000)
            gift = random.randrange(0, 4000, 500)
            if is_field:
                salary = random.randrange(18000, 32000, 1000)
                total = salary + gen_exp + incentive + gift
            else:
                salary = None                      # staff salary ≠ admission cost
                total = gen_exp + incentive + gift
            conn.execute(
                "INSERT INTO execs (agm_id, name, created_at, salary, gen_exp, "
                "incentive, gift, total_amount, target) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (agm_id, name) DO NOTHING",
                (agm_id, ename, now, salary, gen_exp, incentive, gift, total,
                 random.randint(25, 80)))
            agm_execs[name].append(ename)

    # ---- Applicants: ~1,500 fictional rows across the whole funnel ----------
    # (campus, weight) — most volume at the NORTHVALE campuses.
    campus_mix = [("NORTHVALE DS", 55), ("NORTHVALE HOSTEL", 20),
                  ("EASTPORT DS", 15), ("WESTBROOK DS", 10)]
    status_mix = [("REPORTED", 52), ("SETTLED", 14), ("YET TO ARRIVE", 16),
                  ("NOT LIFTING", 11), ("DROPPED", 7)]
    raw_variants = {
        "REPORTED":      ["REPORTED", "REPORTED - JOINED", "REPORTED (HOSTEL)"],
        "SETTLED":       ["SETTLED", "FEE SETTLED"],
        "YET TO ARRIVE": ["YET TO ARRIVE", "WILL COME AFTER RESULTS"],
        "NOT LIFTING":   ["NOT LIFTING", "SWITCHED OFF", "NO RESPONSE"],
        "DROPPED":       ["DROPPED", "JOINED ELSEWHERE"],
    }
    campus_by_city = {c: city for city, cs in CITIES.items() for c in cs}
    agms_by_city = {}
    for name, city, is_field, rent in AGMS:
        agms_by_city.setdefault(city, []).append(name)

    total = 1500
    print(f"Seeding {total} fictional applicants ...")
    rows = []
    for i in range(1, total + 1):
        campus = random.choices([c for c, _ in campus_mix],
                                [w for _, w in campus_mix])[0]
        status = random.choices([s for s, _ in status_mix],
                                [w for _, w in status_mix])[0]
        assert status in STATUSES
        agm = random.choice(agms_by_city[campus_by_city[campus]])
        exec_name = random.choice(agm_execs[agm])
        course = random.choice(CAMPUS_COURSES[campus])
        name, father_name = unique_name()
        name, father_name = name.upper(), father_name.upper()
        reported = (day(random.randint(0, 45))
                    if status in ("REPORTED", "SETTLED") else None)
        fee = (random.randrange(45000, 86000, 500)
               if status in ("REPORTED", "SETTLED") else None)
        hostel = (random.choice(("AC", "NON-AC"))
                  if "HOSTEL" in campus or random.random() < 0.35 else None)
        rows.append((f"26A{i:04d}", name, father_name,
                     course, course, fake_phone(),
                     fake_phone() if random.random() < 0.4 else None,
                     agm, exec_name, campus, fee, hostel,
                     random.choice(raw_variants[status]), status, reported,
                     0, "demo-seed", now))
    cur = conn.raw.cursor()
    cur.executemany(
        "INSERT INTO students (appn_no, student_name, father_name, grp, "
        "application_course, mobile1, mobile2, agm, marketing_exec, campus, "
        "final_fee, hostel, status_raw, status_category, reported_date, hidden, "
        "registered_by, registered_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "
        "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", rows)

    # ---- Activity + login logs ----------------------------------------------
    log_users = [(ADMIN_USERNAME, "Administrator", "admin"),
                 ("editor", "Meghana Kulkarni", "editor"),
                 ("editor.northvale", "Sameer Joshi", "editor")]
    edits = [("students", "student_update", "Updated an admission"),
             ("students", "student_add", "Added an admission"),
             ("org", "exec_create", "Added a marketing exec"),
             ("org", "campus_rename", "Renamed a campus")]
    for _ in range(15):
        uname, full, role = random.choice(log_users)
        module, action, detail = random.choice(edits)
        u = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        conn.execute(
            "INSERT INTO edit_log (user_id, username, full_name, role, module, "
            "action, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (u["id"], uname, full, role, module, action, detail,
             day(random.randint(0, 12)) + f" {random.randint(9, 19):02d}:{random.randint(0, 59):02d}"))
    for _ in range(10):
        uname, full, role = random.choice(log_users)
        u = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        conn.execute(
            "INSERT INTO login_log (user_id, username, full_name, role, event, "
            "ip, created_at) VALUES (?, ?, ?, ?, 'login', '203.0.113.20', ?)",
            (u["id"], uname, full, role,
             day(random.randint(0, 8)) + f" {random.randint(8, 20):02d}:40"))


if __name__ == "__main__":
    main()

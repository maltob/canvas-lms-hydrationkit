from copy import deepcopy
import json
from faker import Faker
import random
import csv
import os
from hashlib import md5

if os.environ.get('USEOLLAMA'):
    import ollama

fake = Faker('en_US')
takenEmails = []
takenUIDs = []

#Build users for the tenant
def generateUser(domain: str = "canvas.test"):
    irange = []
    for i in range(10):
        irange.append(str(i))
    uid = ''.join(random.choices(irange,k=9))
    while uid in takenUIDs:
        uid = ''.join(random.choices(irange,k=9))

    first = fake.first_name_female()
    last = fake.last_name_female()
    pronoun = 'she/her'
    change = random.randint(0,4)
    dut_change = random.randint(0,20)
    declared_user_type = "student"
    if dut_change == 1:
        declared_user_type = "teacher"
    status = "active"
    stat_change = random.randint(0,90)
    if stat_change == 1:
        status = "deleted"
    if stat_change == 2:
        status = "suspended"

    match change:
        case 1:
            first = fake.first_name_male()
            last = fake.last_name_male()
            pronoun = 'he/him'
        case 2:
            first = fake.first_name_nonbinary()
            last = fake.last_name_nonbinary()
            pronoun = random.choices(['ze/zir','xe/xyr','they/them'])
        case 3:
            first = fake.first_name()
            last = fake.last_name()
            pronoun = ''

    email = f"{first.lower()}.{last.lower()}@{domain}"
    i = 0
    while email in takenEmails:
        email = f"{first.lower()}.{last.lower()}{i}@{domain}"
        i += 1
    takenEmails.append(email)
    
    return {
        "user_id": uid,
        "login_id": email,
        "email": email,
        "first_name": first,
        "last_name": last,
        "pronoun": pronoun,
        "declared_user_type": declared_user_type,
        "status": status
    }

def generateCourses(subject: str, terms: list, minCourseNum=100, maxCourseNumber=450):
    courses = []
    
    #Generate between 3 and 12 courses for this subject
    for _ in range(3,random.randint(1,12)):
        courseCode = random.randint(minCourseNum,maxCourseNumber)
        courseTitle = fake['en-US'].sentence()
        if os.environ.get('USEOLLAMA'):
            response = ollama.chat(model='phi3', messages=[
                {
                    'role': 'user',
                    'content': f'Create a course title for {courseCode}, keep in mind it is related to {subject}. Only output the course title.',
                },
            ])
            courseTitle = response['message']['content'].strip().replace('"','') 
        for term in terms:
            start_date = term["start_date"]
            end_date = term["end_date"]
            status = "active"
            stat_change = random.randint(0,90)
            if stat_change == 1:
                status = "deleted"
            courses.append( {
                'course_id':md5(bytes(term["term_id"]+subject+str(courseCode),encoding='UTF-8')).hexdigest(), 
                        "short_name":subject+"-"+str(courseCode)+" "+term["term_id"],
                        "long_name":term["name"]+" "+subject+"-"+str(courseCode)+" - "+courseTitle,
                        "account_id":subject,"term_id":term["term_id"],"start_date":start_date,"end_date":end_date,
                        "status": status
                        } )
    return courses


def generateSections(course, sectionsPerTermMin: int =2, sectionsPerTermMax: int = 8):
    sections = []
    for i in range(random.randint(sectionsPerTermMin,sectionsPerTermMax)):
        section_id = ("00"+str(i))[:3]
        #Throw in a letter once in a while
        if random.randint(0,4) == 1:
            section_id = "Y"+section_id
        sections.append({
            "section_id": md5(bytes(course["course_id"]+section_id,encoding='UTF-8')).hexdigest(),
            "name":course["short_name"]+"-"+section_id,
            "course_id":course["course_id"],
            "status":course["status"]
        } )
    return sections

#Only run the base generation if the csv does't exist
if not os.path.exists("data/users.csv"):

    users = []
    for _ in range(800):
        users.append(generateUser())


    with open('data/users.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["user_id", "login_id", "email", "first_name", "last_name", "pronoun","declared_user_type","status"])
        writer.writeheader()
        for entry in users:
            writer.writerow(entry)

    #users = []
    #with open(("data/users.csv"), newline='') as f:
    #    reader = csv.DictReader(f)
    #    users += list(reader)

    terms = []
    with open(("data/terms.csv"), newline='') as f:
        reader = csv.DictReader(f)
        terms += list(reader)

    subjects = ("BIO","CSC","NUR","ENG","ECO","PSY","MAT","ART")
    courses = []
    Faker.seed(random.randint(0,99999))
    for subject in subjects:
        courses= courses+ generateCourses(subject=subject,terms=terms)




    with open('data/courses.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["course_id", "short_name", "long_name", "account_id", "term_id", "start_date","end_date","status"])
        writer.writeheader()
        for entry in courses:
            writer.writerow(entry)

    sections = []
    for course in courses:
        sections = sections +generateSections(course)

    with open('data/sections.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["section_id", "name","long_name", "course_id","status"])
        writer.writeheader()
        for entry in sections:
            writer.writerow(entry)


    #with open(("data/sections.csv"), newline='') as f:
    #    reader = csv.DictReader(f)
    #    sections += list(reader)

    def generate_enrollments(user,sect):
        role = user['declared_user_type']
        status = "active"
        r = random.randint(0,60)
        if r == 45:
            if role == "teacher":
                role="student"
            else:
                role = "teacher"
        if r == 2:
            status="deleted"
        if r == 5:
            status="completed"
        if role == "teacher" or (sect["course_id"] not in user_courses[(user["user_id"])]):
            sections_enrollments[(sect["section_id"])].append(
                {
                    "section_id": sect["section_id"],
                    "user_id": user["user_id"],
                    "status":status,
                    "role":role
                })
        if role == "student" and sect["course_id"] not in user_courses[(user["user_id"])]:
            user_courses[(user["user_id"])].append(sect["course_id"])
        #if role == "teacher" and status == "active" and sect['section_id'] in sections_without_teacher:
            #sections_without_teacher.pop([(sect['section_id'])])

    sections_without_teacher = {}
    sections_enrollments = {}
    #Try some avoidance of adding the student in multiple sections of the same course
    user_courses = {}
    for user in users:
        user_courses[(user["user_id"])]=[]

    for section in sections:
        sections_enrollments[(section["section_id"])]=[]
        sections_without_teacher[section["section_id"]] = section

    for user in users:
        #Create  enrollments for teachers
        k =random.randint(3,25)
        if user['declared_user_type'] == "teacher" and len(sections_without_teacher) > k :
            for _ in range(k):
                    generate_enrollments(user,sections_without_teacher.popitem()[1])
        #generate enrollments for everyone eelse
        for sect in random.choices(sections,k=random.randint(10,25)):
            generate_enrollments(user,sect)


    enrollments = []
    for sect_enroll in sections_enrollments:
        enrollments += sections_enrollments[sect_enroll]

    with open('data/enrollments.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["section_id", "user_id","status", "role"])
        writer.writeheader()
        for entry in enrollments:
            writer.writerow(entry)



if not os.environ.get('USEOLLAMA'):
    print("Closing script as LLAMA is not enabled")
    quit()
####
#
# Everything below is AI generated
#
####
university_name = "Canvas Test University"

course_map = {}
for course in courses:
    course_map[course['course_id']] = course
section_map = {}
for section in sections:
    section_map[section['section_id']] = section['course_id']

# Generate profiles for each student. Will populate on Canvas then later use for reponses to quizes and questions.
user_profiles = {}

if not users:
    users = []
    with open(("data/users.csv"), newline='') as f:
       reader = csv.DictReader(f)
       users += list(reader)
    user_courses = {}
    #Probably need to reload the users and enrollments from the enrollment file
    with open('data/enrollments.csv', mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for enrollment in list(reader):
            if enrollment["user_id"] not in user_courses.keys():
                user_courses[enrollment["user_id"]] = []
            user_courses[enrollment["user_id"]].append((section_map[enrollment["section_id"]]))
            #print(section_map[enrollment["section_id"]])

with open(("api_data/user_profiles.csv"), newline='') as f:
    reader = csv.DictReader(f)
    for profile in list(reader):
        user_profiles[profile["user_id"]] = profile

with open(("data/courses.csv"), newline='') as f:
    reader = csv.DictReader(f)
    for course in list(reader):
        courses.append(course)

for user in users:
    if user["user_id"] not in user_profiles.keys():
        age = random.randint(17,random.randint(22,random.randint(25,80)))
        user_enrollments = user_courses[user["user_id"]]
        action = "taken"
        if user['declared_user_type'] == "teacher":
            action = "taught"
            age = random.randint(24,random.randint(40,80))
        #Get other courses or they'll all seem to like Computer Science
        user_course_enrollments = []
        for enroll in user_enrollments:
            ctitle = course_map[enroll]['long_name'].split(" - ")[1]
            user_course_enrollments.append(ctitle)
        #The AI focused too much on the courses 
        bio_resp = ollama.generate("phi3",f"You are {user['first_name']} {user['last_name']} and your pronouns are {user['pronoun']} who is a {age} {user['declared_user_type']} currently at {university_name}. You are {action} courses here, your favorite is {user_course_enrollments[random.randint(0,len(user_course_enrollments)-1)]}.  The job of a {fake.job()}.  Please write a short paragraph about yourself including hobbies.")
        user_profiles[user['user_id']] = {"user_id":user['user_id'], "bio":bio_resp['response'], "age":age, "first":user['first_name'],"last":user['last_name'], "pronouns":user['pronoun'],"declared_user_type":user['declared_user_type']}
    #Save every 20 user profiles
    if len(user_profiles) % 20 == 0:
        print(f"Saving profiles at {len(user_profiles)} generated.")
        with open('api_data/user_profiles.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["user_id", "age","first", "last", "pronouns", "declared_user_type","bio"])
            writer.writeheader()
            for entry in user_profiles:
                _ = writer.writerow(user_profiles[entry])
#Save out all
with open('api_data/user_profiles.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["user_id", "age","first", "last", "pronouns", "declared_user_type","bio"])
            writer.writeheader()
            for entry in user_profiles:
                _ = writer.writerow(user_profiles[entry])

#Generate a few discussions per course
course_discussions = []
generated_discussion_ids = []
with open(("api_data/course_discussions.csv"), newline='') as f:
    reader = csv.DictReader(f)
    for course_d in list(reader):
        generated_discussion_ids.append(course_d['course_id'])
        course_discussions.append(course_d)

for course in courses:
    if course["course_id"] not in generated_discussion_ids:
        discussion_int = random.randint(0,8)
        if discussion_int > 0:
            resp = ollama.generate('phi3',f'Generate {discussion_int} discussion topics for a LMS course about {course["long_name"].split(" - ")[1]} with a topic name and an initial prompt for students to answer as valid json without markdown. Use the keys of "topics" as the root key then "topic_name" and "initial_prompt" for each discussion ')['response']
            arr = None
            while(arr == None):
                try:
                    arr = json.loads(resp)['topics']
                    for item in arr:
                        course_discussions.append({
                            'course_id': course['course_id'],
                            'discussion_topic_title': item['topic_name'],
                            'discussion_topic_prompt': item['initial_prompt'],
                        })
                except:
                    print(f"Ollama failed to generate valid JSON for {course['course_id']}. Retrying")
                    resp = ollama.generate('phi3',f'Generate 3 discussion topics for a LMS course about {course["long_name"].split(" - ")[1]} with a topic name and an initial prompt for students to answer as valid json without markdown.  Use the keys of "topics" as the root key then "topic_name" and "initial_prompt" for each discussion')['response']
            generated_discussion_ids.append(course['course_id'])
        else:
            generated_discussion_ids.append(course['course_id'])
        if len(generated_discussion_ids) % 5 == 0:
            print(f"Saving discussions at {len(generated_discussion_ids)} courses generated.")
            with open('api_data/course_discussions.csv', mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=["course_id", "discussion_topic_title","discussion_topic_prompt"])
                writer.writeheader()
                for entry in course_discussions:
                    _ = writer.writerow(entry)

with open('api_data/course_discussions.csv', mode='w', newline='') as file: 
                writer = csv.DictWriter(file, fieldnames=["course_id", "discussion_topic_title","discussion_topic_prompt"])
                writer.writeheader()
                for entry in course_discussions:
                    _ = writer.writerow(entry)

#Generate a few quizzes per course

#Generate several pages per course

#Generate a few assignments per course

#Generate responses to each assignment for each student

#Generate profile pictures using SD?
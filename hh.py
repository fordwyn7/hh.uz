import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from job_list import tools_list
from ai_filter import identify_title

import json
import time
import locale
import csv
import os
import re


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

# ============================================================================
# TOOLS LIST & PATTERNS
# ============================================================================

tool_patterns = []
for tool in tools_list:
    escaped = re.escape(tool).replace(r"\ ", r"\s+")
    pattern_exact = re.compile(r"(?<!\w)" + escaped + r"(?!\w)", re.IGNORECASE)
    tool_patterns.append((tool, pattern_exact))

    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", tool)
    if spaced != tool and " " in spaced:
        escaped_spaced = re.escape(spaced).replace(r"\ ", r"\s+")
        pattern_spaced = re.compile(
            r"(?<!\w)" + escaped_spaced + r"(?!\w)", re.IGNORECASE
        )
        tool_patterns.append((tool, pattern_spaced))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def find_tools_in_text(text):
    text_norm = re.sub(r"\s+", " ", text)
    found = []

    for tool, pattern in tool_patterns:
        if pattern.search(text_norm):
            found.append(tool)

    return sorted(set(found))


def save_to_csv(
    job_id,
    job_title,
    job_title_from_list,
    image_link,
    location,
    skills,
    salary,
    company_name,
    source,
    posted_date,
):
    filename = "jobs.csv"
    file_exists = os.path.isfile(filename)
    if company_name == "":
        company_name = "N/A"
    try:
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, delimiter="|")

            if not file_exists:
                writer.writerow(
                    [
                        "ID",
                        "Posted_date",
                        "Job Title from List",
                        "Job Title",
                        "Company",
                        "Company Logo URL",
                        "Country",
                        "Location",
                        "Skills",
                        "Salary Info",
                        "Source",
                    ]
                )

            writer.writerow(
                [
                    job_id,
                    posted_date,
                    job_title_from_list,
                    job_title,
                    company_name,
                    image_link,
                    "Uzbekistan",
                    location,
                    skills,
                    salary,
                    source,
                ]
            )
        print(f"Saved job {job_id} to CSV.")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)
    return driver


# ============================================================================
# SCRAPING LOGIC
# ============================================================================


def get_hh_vacancies(jobs_list):
    driver = create_driver()
    driver1 = create_driver()

    try:
        for job in jobs_list:
            page = 0

            while True:
                driver.get(
                    f"https://hh.uz/vacancies/{job.replace(' ','-')}?page={page}&hhtmFrom=vacancy_search_list"
                )
                time.sleep(2)

                job_elements = driver.find_elements(
                    By.XPATH, "//a[@data-qa='serp-item__title']"
                )
                job_urls = [el.get_attribute("href") for el in job_elements]

                if not job_urls:
                    break

                location_elements = driver.find_elements(
                    By.XPATH, "//span[@data-qa='vacancy-serp__vacancy-address']"
                )
                locations = [el.text for el in location_elements if el.text != ""]

                if len(job_urls) != len(locations):
                    print(
                        f"Warning: URLs ({len(job_urls)}) and locations ({len(locations)}) count mismatch!"
                    )

                for job_url, location in zip(job_urls, locations):
                    driver1.get(job_url)

                    # Extract job title
                    try:
                        title = (
                            WebDriverWait(driver1, 5)
                            .until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        "//h1[contains(@class,'bloko-header-section')]",
                                    )
                                )
                            )
                            .text
                        )
                    except TimeoutException:
                        title = "N/A"

                    time.sleep(2)

                    # Extract posted date
                    date_location_div = driver1.find_element(
                        By.XPATH, "//div[contains(text(),'Вакансия опубликована')]"
                    )
                    time.sleep(2)
                    span_text = date_location_div.find_element(By.TAG_NAME, "span").text

                    months = {
                        "янв": "01",
                        "фев": "02",
                        "мар": "03",
                        "апр": "04",
                        "май": "05",
                        "июн": "06",
                        "июл": "07",
                        "авг": "08",
                        "сен": "09",
                        "окт": "10",
                        "ноя": "11",
                        "дек": "12",
                    }

                    day, month_rus, year = span_text.split()
                    month = months[month_rus[:3]]
                    posted_date = f"{month}/{day}/{year}"

                    # Extract company name
                    try:
                        company_name = (
                            WebDriverWait(driver1, 5)
                            .until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        "//a[@data-qa='vacancy-company-name']/span",
                                    )
                                )
                            )
                            .text
                        )
                    except TimeoutException:
                        company_name = "N/A"

                    # Extract company logo
                    try:
                        image_element = WebDriverWait(driver1, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//img[contains(@class,'magritte-avatar-image')]",
                                )
                            )
                        )
                        image_link = image_element.get_attribute("src")
                    except TimeoutException:
                        image_link = "N/A"

                    # Extract job description
                    try:
                        desc_el = WebDriverWait(driver1, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//div[@data-qa='vacancy-description' or contains(@class,'g-user-content')]",
                                )
                            )
                        )
                        desc_text = desc_el.text
                    except TimeoutException:
                        desc_text = ""

                    # Extract salary
                    try:
                        salary_el = WebDriverWait(driver1, 4).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//div[contains(@class,'vacancy-salary-compensation-type-gross') or contains(@class,'vacancy-salary') or @data-qa='vacancy-salary']",
                                )
                            )
                        )
                        salary = salary_el.text.strip()

                        if "," in salary:
                            salary = salary.split(",")[0]

                        if not salary:
                            salary = "N/A"
                    except TimeoutException:
                        salary = "N/A"

                    skills_from_page = []
                    try:
                        skill_elements = driver1.find_elements(By.XPATH, "//li[@data-qa='skills-element']")
                        skills_from_page = [el.text.strip() for el in skill_elements if el.text.strip()]
                        cleaned_skills = []
                        for skill in skills_from_page:
                            if skill in tools_list:
                                desc_text += f" {skill} "
                        
                        
                    except Exception as e:
                        print(f"Could not extract skills-element: {e}")
                    matched_tools = find_tools_in_text(desc_text)
                    all_skills = list(set(matched_tools))
                    
                    skills = ", ".join(sorted(all_skills)) if all_skills else ""
                    
                    if "," in location:
                        location = location.split(",")[0]
                    new_title = identify_title(title, all_skills)[0]
                    if new_title != "unknown":
                        job = new_title
                    # Save to CSV
                    try:
                        job_id = driver1.current_url.split("?")[0].split("/")[-1]
                        save_to_csv(
                            job_id=job_id,
                            posted_date=posted_date,
                            job_title_from_list=job,
                            company_name=company_name,
                            image_link=image_link,
                            location=location,
                            skills=skills,
                            job_title=title,
                            salary=salary,
                            source="hh.uz",
                        )
                    except Exception as e:
                        print(f"Failed to save job: {driver1.current_url} - {e}")

                page += 1

    finally:
        driver.quit()
        driver1.quit()


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    with open("job_list.json", "r") as file:
        jobs_list = json.load(file)
    get_hh_vacancies(jobs_list)
    print("Vacancies fetched successfully.")


if __name__ == "__main__":
    main()

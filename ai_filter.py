import google.generativeai as genai
import time

key = "YOUR_API_KEY_HERE"
genai.configure(api_key=key)


def identify_title(titles, skills):
    prompt = f"""
                You are an expert in job title matching. Your task is to map given job titles and skills to the closest match from a predefined list of job titles. Follow these rules carefully:

                ### Predefined Job Titles (Valid Outputs Only):
                - Backend developer
                - Frontend developer
                - Data analyst
                - Data engineer
                - Data scientist
                - AI engineer
                - Android developer
                - IOS developer
                - Game developer
                - DevOps engineer
                - IT project manager
                - Network engineer
                - Cybersecurity Analyst
                - Cloud Architect
                - Full stack developer
                - QA engineer

                ### Input:
                - Job Titles: {titles}
                - Skills: {skills}

                ### Rules:
                1. Match **only** to the predefined list of job titles.
                2. Use both the job title and skills to determine the best match.
                3. If skills are missing, use the job title alone for matching.
                4. If the job title is unclear but skills strongly align with a predefined role, match based on skills.
                5. If neither the job title nor the skills match, return **unknown** for that position.
                6. The number of output job titles **must match** the number of input job titles.
                7. Do **not** invent, hallucinate, or modify job titles beyond the predefined list.

                ### Output:
                Return the matched job titles as a comma-separated list, maintaining the same order as the input titles. For example:
                - Input: ["Junior Developer", "Data Specialist"]
                - Output: "Backend developer, Data analyst"

    """
    try:
        # Create a generative model
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Generate content using the prompt
        # print(titles)
        response = model.generate_content(prompt)
        output_text = response.text.strip()
        output_list = [item.strip() for item in output_text.split(",")]
        # print(output_list) # uncomment for debugging
        print(len(output_list))
        time.sleep(1)
        return output_list

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return ["unknown"] * len(titles)


def processdf(df, chunk_size=10):

    results = []
    for i in range(0, len(df), chunk_size):

        chunk = df.iloc[i : i + chunk_size]
        titles = chunk["Job Title"].tolist()
        skills = chunk["Skills"].tolist()
        matched_titles = identify_title(titles, skills)
        results.extend(matched_titles)
        time.sleep(3)
    return results


def filtercolumns(df, keywordlist):
    results = processdf(df, 10)
    try:
        df["Job Title from List"] = results
        try:
            df["Salary Info"] = df["Salary Info"].fillna(0)
            df = df.fillna("Unknown")
        except:
            pass

        df = df[
            df["Job Title from List"].isin(keywordlist)
            & (df["Job Title from List"] != "unknown")
        ]
        return df
    except Exception as e:
        print(f"error while filtering columns: {e}")

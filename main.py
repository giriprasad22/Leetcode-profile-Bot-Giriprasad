from flask import Flask, render_template, request, jsonify
import requests
import time

app = Flask(__name__)

# Enhanced headers to mimic browser behavior
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://leetcode.com",
    "Referer": "https://leetcode.com/",
}

def get_leetcode_data(username):
    """Fetch LeetCode profile data using GraphQL API with retry logic"""
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            username
            profile { 
                ranking 
            }
            languageProblemCount { 
                languageName 
                problemsSolved 
            }
            submitStats: submitStatsGlobal {
                acSubmissionNum { 
                    difficulty 
                    count 
                }
            }
            badges { 
                name 
            }
        }
    }
    """
    
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"username": username}},
                headers=REQUEST_HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if data.get("errors"):
                error_msg = data["errors"][0].get("message", "Unknown API error")
                if "exceeded" in error_msg.lower():  # Rate limit error
                    time.sleep(2)  # Wait before retrying
                    continue
                return {"errors": [{"message": error_msg}]}
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == 2:  # Last attempt
                return {"errors": [{"message": f"Network error: {str(e)}"}]}
            time.sleep(1)  # Wait before retrying
            
    return {"errors": [{"message": "API request failed after multiple attempts"}]}

@app.route("/", methods=["GET", "POST"])
def home():
    current_time = time.strftime("%I:%M %p")  # Get current time for messages
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            return render_template(
                "index.html", 
                error="Username cannot be empty",
                current_time=current_time
            )
        
        print(f"\nFetching data for: {username}")  # Debug output
        
        data = get_leetcode_data(username)
        print("API Response:", data)  # Debug output
        
        # Check if user exists and data is valid
        if data.get("data") and data["data"].get("matchedUser"):
            user_data = data["data"]["matchedUser"]
            
            # Process problems by difficulty
            problems = {}
            total_solved = 0
            if user_data.get("submitStats") and user_data["submitStats"].get("acSubmissionNum"):
                for stat in user_data["submitStats"]["acSubmissionNum"]:
                    if stat["difficulty"] == "All":
                        total_solved = stat["count"]
                    else:
                        problems[stat["difficulty"]] = stat["count"]
            
            # Process languages (limit to top 5)
            languages = {}
            if user_data.get("languageProblemCount"):
                sorted_langs = sorted(
                    user_data["languageProblemCount"], 
                    key=lambda x: x["problemsSolved"], 
                    reverse=True
                )[:5]
                for lang in sorted_langs:
                    if lang["problemsSolved"] > 0:
                        languages[lang["languageName"]] = lang["problemsSolved"]
            
            # Process badges
            badges = []
            if user_data.get("badges"):
                badges = [badge["name"] for badge in user_data["badges"]]
            
            # Get ranking
            ranking = None
            if user_data.get("profile") and user_data["profile"].get("ranking"):
                ranking = user_data["profile"]["ranking"]
            
            stats = {
                "username": username,
                "rank": ranking,
                "problems": problems,
                "languages": languages,
                "badges": badges,
                "total_solved": total_solved
            }
            
            return render_template(
                "index.html", 
                stats=stats,
                current_time=current_time
            )
        
        # Handle errors
        error_msg = "User not found or profile is private"
        if data.get("errors"):
            error_msg = data["errors"][0].get("message", error_msg)
        
        return render_template(
            "index.html", 
            error=error_msg,
            current_time=current_time
        )
    
    # Initial GET request
    return render_template("index.html", current_time=current_time)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
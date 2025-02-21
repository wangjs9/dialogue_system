from fastapi import FastAPI, Form, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import os.path
import random
import json
import time
from typing import List
from datetime import datetime
import uvicorn
from user_interface.model_response import get_model_response

# from vllm import LLM, SamplingParams
# from peft import PeftModel
# import torch

users = json.load(open("./user_interface/users.json", "r"))

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key="your_secret_key",  # Change this to a secure random value
    session_cookie="session_id",  # Name of the session cookie
    same_site="lax",  # Allows session persistence across requests
    max_age=3600,  # Session expires after 1 hour
    https_only=False  # Set to True in production with HTTPS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allow all origins (or specify frontend: ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allow all headers
)

app.mount("/static", StaticFiles(directory="user_interface/static"), name="static")
templates = Jinja2Templates(directory="./user_interface/templates")


@app.get("/")
@app.get("/login")
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    """Handle user login and store session data."""

    if username in users and users[username] == password:
        user_mode = "member"  # ✅ Registered user
    elif username not in users and password == "test_mode":
        user_mode = "anonymous"  # ✅ Experiment mode user
    else:
        return JSONResponse(content={
            "success": False,
            "message": "用户名或密码无效。请重新输入。\nInvalid username or password. Please try again."
        })

    # ✅ Store username in session
    current_time = datetime.fromtimestamp(time.time()).strftime("%y-%m-%d-%H-%M-%S")
    request.session["username"] = username
    request.session["user_mode"] = user_mode
    request.session["start_time"] = current_time

    # ✅ Set cookies for session and user mode
    response.set_cookie(key="session_id", value=username, httponly=True)
    response.set_cookie(key="user_mode", value=user_mode, httponly=True)  # New cookie for mode
    response.set_cookie(key="start_time", value=current_time, httponly=True)  # New cookie for mode

    return JSONResponse(content={
        "success": True,
        "username": username,
        "user_mode": user_mode,  # ✅ Ensure frontend receives this
        "message": "Login successful!"
    })


class PreQuestionRequest(BaseModel):
    description: str
    keywords: List[str]


@app.post("/submit-pre-questions", response_class=HTMLResponse)
async def pre_questions(request: Request, question_answer: PreQuestionRequest):
    username = request.session.get("username", "")
    user_mode = request.session.get("user_mode", "")
    start_time = request.session.get("start_time", "")

    if not question_answer.keywords:
        raise HTTPException(status_code=400, detail="At least one keyword is required.")

    prequestions = question_answer.dict()
    json.dump(
        {"username": username, "user_mode": user_mode, "start_time": start_time, "presurvey": prequestions,
         "dialogue": [], "feedback": [], "ratings": []},
        open(f"user_interface/dialogues/{username}_{start_time}.json", "w"),
        indent=4
    )


@app.get("/pre-questions", response_class=HTMLResponse)
async def pre_questions(request: Request):
    username = request.session.get("username", "")
    user_mode = request.session.get("user_mode", "")
    return templates.TemplateResponse(
        "questions.html",
        {"request": request, "username": username, "user_mode": user_mode}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve chatbot dashboard."""
    username = request.session.get("username", "")
    user_mode = request.session.get("user_mode", "")
    start_time = request.session.get("start_time", "")

    if not username or user_mode not in ["member", "anonymous"]:
        return HTMLResponse(content="""
            <script>
                alert("403 Forbidden: Access Denied. You must log in first.");
                window.location.href = "/";
            </script>
            """, status_code=403)
    if not os.path.exists(f"user_interface/dialogues/{username}_{start_time}.json"):
        json.dump(
            {"username": username, "user_mode": user_mode, "start_time": start_time, "dialogue": [], "feedback": [],
             "ratings": []},
            open(f"user_interface/dialogues/{username}_{start_time}.json", "w"),
            indent=4
        )

    # if user_mode == "member":
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "username": username, "user_mode": user_mode, "start_time": start_time}
    )


@app.post("/chat")
async def chatbot_api(request: Request, message: str = Form(...)):
    """Chatbot generates two responses for user selection."""
    # responses = {
    #     "hello": ["Hi there! How can I help you?", "Hello! What can I do for you?"],
    #     "how are you": ["I'm doing great! How about you?", "I'm a bot, but I'm feeling fantastic!"],
    #     "bye": ["Goodbye! Have a great day!", "See you next time! Take care!"],
    # }
    current_time = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    # Retrieve session data (if applicable)
    username = request.session.get("username", "anonymous")
    start_time = request.session.get("start_time", current_time)
    # Save dialogue history

    dialogue_path = f"user_interface/dialogues/{username}_{start_time}.json"

    try:
        with open(dialogue_path, "r") as file:
            dialogue = json.load(file)
    except FileNotFoundError:
        dialogue = {"dialogue": []}

    dialogue["dialogue"].append({"role": "user", "content": message, "time": current_time})

    responses = get_model_response(dialogue["dialogue"])
    reply_options = [responses['dpo'], responses['sft']]
    random.shuffle(reply_options)
    dialogue["dialogue"].append(
        {"role": "assistant", "time": current_time, "sft": responses["sft"], "dpo": responses["dpo"]})
    if responses["is_english"]:
        dialogue["dialogue"][-2]["translated_content"] = responses["translated_content"]
        dialogue["dialogue"][-1]["chinese_sft"] = responses["chinese_sft"]
        dialogue["dialogue"][-1]["chinese_dpo"] = responses["chinese_dpo"]

    with open(dialogue_path, "w") as file:
        json.dump(dialogue, file, indent=4)

    return JSONResponse(content={"response_id": len(dialogue["dialogue"]), "reply_options": reply_options})


@app.post("/selected_response")
async def selected_response(request: Request, message: str = Form(...)):
    current_time = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    username = request.session.get("username", "anonymous")
    start_time = request.session.get("start_time", "")
    dialogue_path = f"user_interface/dialogues/{username}_{start_time}.json"
    try:
        with open(dialogue_path, "r") as file:
            dialogue = json.load(file)
            dialogue["dialogue"][-1]["content"] = message
    except FileNotFoundError:
        dialogue = {"dialogue": []}
        dialogue["dialogue"].append({"content": message, "time": current_time})

    with open(dialogue_path, "w") as file:
        json.dump(dialogue, file, indent=4)

    return JSONResponse(content={"response_id": len(dialogue["dialogue"]), "reply": message})


# Collect user feedback
@app.post("/feedback")
async def collect_feedback(request: Request, response_id: str = Form(...), feedback: str = Form(...)):
    """Store user feedback for chatbot responses."""
    print(f"Feedback received: Response ID {response_id}, Feedback: {feedback}")
    username = request.session.get("username", "")
    start_time = request.session.get("start_time", "")
    current_time = datetime.fromtimestamp(time.time()).strftime("%y-%m-%d-%H-%M-%S")
    feedbacks = json.load(open(f"user_interface/dialogues/{username}_{start_time}.json", "r"))
    feedbacks["feedback"].append({"response_id": response_id, "feedback": feedback, "time": current_time})
    json.dump(feedbacks, open(f"user_interface/dialogues/{username}_{start_time}.json", "w"), indent=4)
    return JSONResponse(content={"message": "Feedback received!"})


@app.post("/rating")
async def collect_rating(request: Request, response_id: str = Form(...), rating: int = Form(...)):
    """Store user feedback for chatbot responses."""
    print(f"Feedback received: Response ID {response_id}, Feedback: {rating}")
    username = request.session.get("username", "")
    start_time = request.session.get("start_time", "")
    current_time = datetime.fromtimestamp(time.time()).strftime("%y-%m-%d-%H-%M-%S")
    ratings = json.load(open(f"user_interface/dialogues/{username}_{start_time}.json", "r"))
    ratings["ratings"].append({"response_id": response_id, "rating": rating, "time": current_time})
    json.dump(ratings, open(f"user_interface/dialogues/{username}_{start_time}.json", "w"), indent=4)
    return JSONResponse(content={"message": "Feedback received!"})


@app.get("/survey")
async def survey(request: Request):
    username = request.session.get("username", "")
    user_mode = request.session.get("user_mode", "")
    start_time = request.session.get("start_time", "")

    if not username or user_mode != "anonymous":
        return HTMLResponse(content="""
                <script>
                    alert("403 Forbidden: Access Denied. You must log in first.");
                    window.location.href = "/";
                </script>
                """, status_code=403)
    return templates.TemplateResponse(
        "survey.html",
        {"request": request, "username": username, "user_mode": user_mode, "start_time": start_time}
    )


class SurveyResponse(BaseModel):
    calm_excited: int
    unpleasant_pleasant: int
    supportiveness: int
    engagement: int


@app.post("/overall_feedback")
async def collect_survey(response: SurveyResponse, request: Request):
    """Collect survey responses and store them."""

    # ✅ Get session data
    username = request.session.get("username", "")
    start_time = request.session.get("start_time", "")

    # ✅ Debugging: Print request metadata
    print(f"User: {username}, Client IP: {request.client.host}")
    print("Survey Data:", response.dict())

    user_content = json.load(open(f"user_interface/dialogues/{username}_{start_time}.json", "r"))
    user_content["post-survey"] = {
        "calm_excited": response.calm_excited,
        "unpleasant_pleasant": response.unpleasant_pleasant,
        "supportiveness": response.supportiveness,
        "engagement": response.engagement
    }
    json.dump(user_content, open(f"user_interface/dialogues/{username}_{start_time}.json", "w"), indent=4)

    # ✅ Clear session data
    request.session.clear()

    # ✅ Redirect to login page
    return JSONResponse(content={"message": "Thank you for your paticipance!", "success": True}, status_code=200)


@app.get("/logout")
async def logout(request: Request, response: Response):
    """Clear session and redirect to login page."""
    request.session.clear()  # ✅ Remove session data
    response.delete_cookie("session_id")  # ✅ Delete session cookie
    # return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # uvicorn.run(app, host="127.0.0.1", port=8000)

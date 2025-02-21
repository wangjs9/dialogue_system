document.addEventListener("DOMContentLoaded", function () {
    let userResponse = ""; // Store the first response
    let selectedKeywords = []; // Store selected keywords

    const chatMessage = document.getElementById("chat_message");
    const sendMessageContainer = document.getElementById("sendmessage");
    const sendButton = document.getElementById("send");
    const userInput = document.getElementById("user_input");

    sendButton.addEventListener("click", function () {
        const userInputValue = userInput.value.trim();
        if (!userInputValue) {
            alert("请输入你的回答 / Please enter your response.");
            return;
        }

        userResponse = userInputValue;

        // Append User Response
        chatMessage.innerHTML += `
            <div class="user-container">
                <div class="user-info">
                    <span class="user-name">${username}</span>
                    <img src="/static/images/user.png" class="avatar user-avatar" alt="User Avatar">
                </div>
                <div class="message user">${userInputValue}</div>
            </div>
        `;

        // Remove input box entirely
        sendMessageContainer.innerHTML = "";

        // Append Second Bot Question
        let botBubble = document.createElement("div");
        botBubble.classList.add("bot-container");
        botBubble.innerHTML = `
            <div class="bot-info">
                <img src="/static/images/bear.jpg" class="avatar bot-avatar" alt="Bot Avatar">
                <span class="bot-name">问卷 / Questions</span>
            </div>
            <div class="message bot">你可以提供一些关键词吗？选择适合你的选项 (最多2个)。<br>Can you give me some keywords? Please select up to 2 options.</div>
            <div class="keyword-buttons">
                <button class="keyword-button" data-keyword="工作 Work">工作 Work</button>
                <button class="keyword-button" data-keyword="学习 Study">学习 Study</button>
                <button class="keyword-button" data-keyword="生活 Life">生活 Life</button>
                <button class="keyword-button" data-keyword="家庭 Family">家庭 Family</button>
                <button class="keyword-button" data-keyword="朋友 Friend">朋友 Friend</button>
                <button class="keyword-button" data-keyword="亲密关系 Relationship">亲密关系 Relationship</button>
                <button class="keyword-button" data-keyword="身体健康 Physical Health">身体健康 Physical Health</button>
                <button class="keyword-button" data-keyword="金钱财务 Finance">金钱财务 Finance</button>
                <button class="keyword-button" data-keyword="忙碌的项目 Deadlines">忙碌的项目 Deadlines</button>
                <button class="keyword-button" data-keyword="其他 Others">其他 Others</button>
            </div>
        `;

        chatMessage.appendChild(botBubble);

        // Replace input area with "Submit & Start Chat" button
        sendMessageContainer.innerHTML = `
            <button id="submit-prequestions" disabled>提交并开始聊天 / Submit & Start Chat</button>
        `;

        sendMessageContainer.classList.remove("hidden");

        const submitButton = document.getElementById("submit-prequestions");

        // Add event listeners for keyword selection
        document.querySelectorAll(".keyword-button").forEach(button => {
            button.addEventListener("click", function () {
                const keyword = this.getAttribute("data-keyword");

                if (selectedKeywords.includes(keyword)) {
                    selectedKeywords = selectedKeywords.filter(k => k !== keyword);
                    this.classList.remove("selected");
                } else {
                    if (selectedKeywords.length >= 2) {
                        alert("最多只能选择两个关键词 / You can select up to 2 keywords.");
                        return;
                    }
                    selectedKeywords.push(keyword);
                    this.classList.add("selected");
                }

                // Enable submit button if at least one keyword is selected
                submitButton.disabled = selectedKeywords.length >= 1 ? false : true;
            });
        });

        // Submit button behavior with error handling
        submitButton.addEventListener("click", async function () {
            console.log(selectedKeywords.length)
            console.log("Hello")
            if (selectedKeywords.length === 0) {
                alert("请选择至少一个关键词 / Please select at least one keyword before proceeding.");
            }

            const data = {
                description: userResponse, keywords: selectedKeywords
            };

            try {
                let response = await fetch("/submit-pre-questions", {
                    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error("Error Response:", errorData);
                    throw new Error("提交失败，请重试 / Submission failed. Please try again.");
                }

                window.location.href = "/dashboard"; // ✅ Redirect to chatbot after submission
            } catch (error) {
                alert(error.message);
            }
        });
    });
});
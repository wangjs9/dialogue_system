$(document).ready(function () {
    if (userMode === "anonymous") {
        $("body").attr("mode", "anonymous");
    }

    console.log("Username:", username);
    console.log("User Mode:", userMode);

    let pendingFeedback = 0;
    let waitingForBot = false;

    function scrollToBottom() {
        let chatBox = $("#chat_message");
        chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    function updateInputState() {
        if (waitingForBot || (userMode === "anonymous" && pendingFeedback > 0)) {
            $("#user_input, #send").prop("disabled", true).css("opacity", "0.5");
        } else {
            $("#user_input, #send").prop("disabled", false).css("opacity", "1");
        }
    }

    updateInputState();

    $("#send").click(function () {
        let userMessage = $("#user_input").val().trim();
        let responseId = $("#chat_message .message").length + 1;
        if (userMessage === "") return;

        if (waitingForBot) {
            alert("请等待模型回复。\nPlease wait for the chatbot to respond before sending a new message.");
            return;
        }

        if (userMode === "anonymous" && pendingFeedback > 0) {
            alert("请提供反馈。\nPlease provide feedback before sending a new message.");
            return;
        }

        waitingForBot = true;
        updateInputState();

        $("#chat_message").append(`
            <div class="user-container">
                <div class="user-info">
                    <span class="user-name">${username}</span>
                    <img src="/static/images/user.png" class="avatar user-avatar" alt="User Avatar">
                </div>
                <div class="message user">${userMessage}</div>
                ${userMode === "anonymous" ? `
                <div class="feedback-section" data-response-id="${responseId}" style="right: 0; width: auto;">
                    <div class="feedback-group" style="display: inline-block;">
                        <p class="feedback-label">心情变化 Emotion Change:</p>
                        <div class="feedback-buttons">
                            <button class="thumb-up">👍</button>
                            <button class="tie">🤝</button>
                            <button class="thumb-down">👎</button>
                        </div>
                    </div>
                </div>
                ` : ""}
            </div>
        `);

        $("#user_input").val("");
        scrollToBottom();

        $.post("/chat", {message: userMessage}, function (response) {
            let responseId = response.response_id;
            let replyOptions = response.reply_options; // Expecting two responses

            if (userMode === "anonymous") {
                pendingFeedback++;
            }

            $("#chat_message").append(`
                <div class="bot-container" data-response-id="${responseId}">
                    <div class="bot-info">
                        <img src="/static/images/bear.jpg" class="avatar bot-avatar" alt="Bot Avatar">
                        <span class="bot-name">同理心倾听者 Empathetic-Listener</span>
                    </div>
                    <p class="instruction">请选择一个更好的回答： / Please select one preferred response:</p>
                    <div class="bot-response-container">
                        <div class="message bot response-option" data-response="${replyOptions[0]}">${replyOptions[0]}</div>
                        <div class="message bot response-option" data-response="${replyOptions[1]}">${replyOptions[1]}</div>
                    </div>
                </div>
            `);

            // **确保两个气泡的宽度和高度一致**
            setTimeout(() => {
                let maxHeight = Math.max(
                    $(".bot-container:last .response-option").eq(0).outerHeight(),
                    $(".bot-container:last .response-option").eq(1).outerHeight()
                );

                $(".bot-container:last .response-option").css({
                    "height": maxHeight + "px"
                });
            }, 100);

            scrollToBottom();
            waitingForBot = false;
            updateInputState(waitingForBot, pendingFeedback);
        }).fail(function () {
            alert("错误：机器人未响应，请重试。");
            waitingForBot = false;
            updateInputState(waitingForBot, pendingFeedback);
        });
    });

    // Handle response selection
    $("#chat_message").on("click", ".response-option", function () {
        let responseContainer = $(this).closest(".bot-container");
        let responseId = responseContainer.data("response-id");

        // **获取选中的文本内容**
        let selectedText = $(this).text();

        // 隐藏未选中的气泡和指令文本
        responseContainer.find(".response-option").not(this).fadeOut(200, function () {
            $(this).remove();
        });
        responseContainer.find(".instruction").fadeOut(200, function () {
            $(this).remove();
        });

        // 让选中的气泡变成 Bot 的正式回答（格式一致）
        $(this).addClass("selected-response").removeClass("response-option").css({
            "cursor": "default"
        });

        // **插入 Bot 的最终回答**
        responseContainer.find(".bot-response-container").replaceWith(`
            <div class="message bot">${selectedText}</div>
        `);

        $.ajax({
            url: "/selected_response",
            type: "POST",
            data: new URLSearchParams({
                response_id: responseId,
                message: selectedText  // ✅ Match FastAPI's `message` parameter
            }).toString(),
            contentType: "application/x-www-form-urlencoded",  // ✅ Ensure Form encoding
            success: function () {
                console.log("✅ Selected response successfully sent to server.");
            },
            error: function () {
                console.error("❌ Error sending selected response to server.");
            }
        });

        let feedbackHtml = userMode === "anonymous" ? `
            <div class="feedback-group">
                <p class="feedback-label">心情变化 Emotion Change:</p>
                <div class="feedback-buttons">
                    <button class="thumb-up">👍</button>
                    <button class="tie">🤝</button>
                    <button class="thumb-down">👎</button>
                </div>
            </div>
        ` : "";

        responseContainer.append(`
            <div class="feedback-section" data-response-id="${responseId}">
                ${feedbackHtml}
                <div class="rating-group">
                    <p class="rating-label">有帮助程度 Supportiveness Level:</p>
                    <div class="rating-scale">
                        ${[...Array(10)].map((_, i) => `<span class="rating-item" data-value="${i + 1}">${i + 1}</span>`).join("")}
                    </div>
                </div>
            </div>
        `);

        scrollToBottom();
    });

    // Handle feedback submission
    $("#chat_message").on("click", ".thumb-up, .thumb-down, .tie", function () {
        let feedbackType = $(this).hasClass("thumb-up") ? "thumb_up" : $(this).hasClass("thumb-down") ? "thumb_down" : "tie";
        let selectedEmoji = feedbackType === "thumb_up" ? "👍" : feedbackType === "thumb_down" ? "👎" : "🤝";
        let responseContainer = $(this).closest(".feedback-section");
        let responseId = responseContainer.data("response-id");

        $.post("/feedback", {response_id: responseId, feedback: feedbackType}, function () {
            responseContainer.find(".feedback-buttons").html(`<span class="feedback-confirmation">Feedback ${selectedEmoji} submitted!</span>`);
            if (userMode === "anonymous") pendingFeedback--;
            updateInputState();
        });
    });

    // Handle rating submission (remains available after feedback)
    $("#chat_message").on("click", ".rating-item", function () {
        let ratingValue = $(this).data("value");
        let responseContainer = $(this).closest(".feedback-section");
        let responseId = responseContainer.data("response-id");

        $.post("/rating", {response_id: responseId, rating: ratingValue}, function () {
            responseContainer.find(".rating-scale").html(`<span class="rating-confirmation">Score ${ratingValue}/10 ⭐ submitted!</span>`);
        });
    });

    $("#close").click(function () {
        window.location.href = userMode === "anonymous" ? "/survey" : "/logout";
    });

    scrollToBottom();
});
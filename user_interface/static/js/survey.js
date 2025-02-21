document.addEventListener("DOMContentLoaded", function () {
    function setupLikertScale(scaleId) {
        console.log(scaleId)
        const scale = document.getElementById(scaleId);
        const items = scale.querySelectorAll(".likert-item");

        items.forEach(item => {
            item.addEventListener("mouseover", function () {
                highlightScale(items, item.dataset.value);
            });

            item.addEventListener("click", function () {
                selectScale(items, item.dataset.value);
            });
        });

        scale.addEventListener("mouseleave", function () {
            resetHighlight(items);
        });
    }

    function highlightScale(items, value) {
        items.forEach(item => {
            item.classList.toggle("selected", item.dataset.value <= value);
        });
    }

    function selectScale(items, value) {
        items.forEach(item => {
            item.classList.toggle("active", item.dataset.value <= value);
        });
    }

    function resetHighlight(items) {
        items.forEach(item => {
            if (!item.classList.contains("active")) {
                item.classList.remove("selected");
            }
        });
    }

    setupLikertScale("scale1");
    setupLikertScale("scale2");
    setupLikertScale("scale3");
    setupLikertScale("scale4");

    document.getElementById("submit-btn").addEventListener("click", async function () {
        const getActiveValue = (scaleId) => {
            const activeItems = document.querySelectorAll(`#${scaleId} .active`);
            return activeItems.length > 0 ? parseInt(activeItems[activeItems.length - 1].dataset.value) : 0;
        };

        console.log("Scale3 Value:", getActiveValue("scale3"));

        const surveyData = {
            calm_excited: getActiveValue("scale1"),
            unpleasant_pleasant: getActiveValue("scale2"),
            supportiveness: getActiveValue("scale3"),
            engagement: getActiveValue("scale4")
        };

        console.log("Survey data JSON:", JSON.stringify(surveyData, null, 2));
        if (Object.values(surveyData).includes(0)) {
            alert("Please select an option for all questions before submitting.");
            return; // ❌ 阻止表单提交
        }

        try {
            const response = await fetch("/overall_feedback", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(surveyData)
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const result = await response.json();
            alert("Survey Submitted!");
            window.location.href = "/login";
        } catch (error) {
            console.error("Error submitting survey:", error);
            alert("Failed to submit survey. Please try again.");
        }
    });
});
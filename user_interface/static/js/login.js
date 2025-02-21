document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");
    const anonymousLoginBtn = document.getElementById("anonymousLogin");
    const passwordField = document.getElementById("password");
    const errorMessage = document.getElementById("errorMessage");
    const loadingSpinner = document.getElementById("loading-spinner");

    // ✅ Function to Handle Login
    function handleLogin(formData) {
        errorMessage.classList.add("hidden");
        errorMessage.innerText = "";
        loadingSpinner.classList.remove("hidden");

        fetch("/login", {
            method: "POST",
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                console.log("API Response:", data);  // ✅ Debugging log
                if (data.success) {
                    // ✅ Store username in localStorage
                    localStorage.setItem("username", data.username);

                    // ✅ Redirect based on user mode
                    if (data.user_mode === "anonymous") {
                        console.log(data.user_mode)
                        window.location.href = "/pre-questions"; // 🔄 Redirect anonymous users
                    } else {
                        console.log(data.user_mode)
                        window.location.href = "/dashboard"; // 🔄 Redirect regular users
                    }
                } else {
                    throw new Error(data.message || "Login failed.");
                }
            })
            .catch(error => {
                errorMessage.innerText = error.message;
                errorMessage.classList.remove("hidden");
            })
            .finally(() => {
                loadingSpinner.classList.add("hidden");
            });
    }

    // ✅ Standard Login - Full Form Submission
    loginForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(this);
        handleLogin(formData);
    });

    // ✅ Experiment Mode Login - Only Username Needed
    anonymousLoginBtn.addEventListener("click", function () {
        const username = document.querySelector('input[name="username"]').value.trim();

        if (!username) {
            errorMessage.innerText = "请输入用户名 / Please enter a username.";
            errorMessage.classList.remove("hidden");
            return;
        }

        // passwordField.removeAttribute("required");
        // passwordField.value = "test_mode"; // Auto-fill password

        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", "test_mode");

        handleLogin(formData);
    });
});
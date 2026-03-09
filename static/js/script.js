document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");

  // ===== LOGIN =====
  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      e.preventDefault();
      clearErrors(loginForm);

      let email = document.getElementById("loginEmail");
      let password = document.getElementById("loginPassword");
      let valid = true;

      if (email.value.trim() === "") {
        showError(email, "Vui lòng nhập email");
        valid = false;
      }

      if (password.value.trim() === "") {
        showError(password, "Vui lòng nhập mật khẩu");
        valid = false;
      }

      if (valid) {
        alert("Đăng nhập thành công!");
        loginForm.reset();
      }
    });
  }

  // ===== REGISTER =====
  if (registerForm) {
    registerForm.addEventListener("submit", function (e) {
      e.preventDefault();
      clearErrors(registerForm);

      let fullname = document.getElementById("fullname");
      let email = document.getElementById("registerEmail");
      let phone = document.getElementById("phone");
      let password = document.getElementById("registerPassword");
      let address = document.getElementById("address");
      let birthday = document.getElementById("birthday");
      let gender = document.querySelector('input[name="gender"]:checked');

      let valid = true;

      if (fullname.value.trim() === "") {
        showError(fullname, "Vui lòng nhập họ tên");
        valid = false;
      }

      if (email.value.trim() === "") {
        showError(email, "Vui lòng nhập email");
        valid = false;
      }

      if (phone.value.trim() === "") {
        showError(phone, "Vui lòng nhập số điện thoại");
        valid = false;
      } else if (!/^[0-9]+$/.test(phone.value)) {
        showError(phone, "Số điện thoại chỉ được nhập số");
        valid = false;
      } else if (phone.value.length < 9 || phone.value.length > 11) {
        showError(phone, "Số điện thoại phải từ 9-11 số");
        valid = false;
      }

      if (password.value.trim() === "") {
        showError(password, "Vui lòng nhập mật khẩu");
        valid = false;
      }

      if (address.value.trim() === "") {
        showError(address, "Vui lòng nhập địa chỉ");
        valid = false;
      }

      if (birthday.value === "") {
        showError(birthday, "Vui lòng chọn ngày sinh");
        valid = false;
      }

      if (!gender) {
        let group = document.querySelector(".gender-group");
        group.classList.add("error");
        showError(group, "Vui lòng chọn giới tính");
        valid = false;
      }

      if (valid) {
        alert("Đăng ký thành công!");
        registerForm.reset();
      }
    });

    // Chặn nhập chữ ở phone
    document.getElementById("phone").addEventListener("input", function () {
      this.value = this.value.replace(/[^0-9]/g, "");
    });
  }

  function showError(element, message) {
    element.classList.add("error");

    let error = document.createElement("div");
    error.className = "error-message";
    error.innerText = message;

    element.parentNode.appendChild(error);
  }

  function clearErrors(form) {
    form.querySelectorAll(".error-message").forEach((e) => e.remove());
    form.querySelectorAll(".error").forEach((e) => e.classList.remove("error"));
  }
});

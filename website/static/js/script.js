const form = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const result = document.getElementById("result");

// Показываем превью для изображений
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file && file.type.startsWith("image/")) {
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  } else {
    preview.style.display = "none";
  }
});

// Отправка файла на сервер через Fetch API
form.addEventListener("submit", (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("fileToUpload", fileInput.files[0]);

  fetch("/upload", {
    method: "POST",
    body: formData
  })
  .then(response => response.text())
  .then(data => {
    result.textContent = data;
    fileInput.value = ""; // очищаем input
    preview.style.display = "none";
  })
  .catch(error => {
    result.textContent = "Ошибка загрузки!";
    console.error(error);
  });
});

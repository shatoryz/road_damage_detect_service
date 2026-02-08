ymaps.ready(init);

function init() {
    var myMap = new ymaps.Map("map", {
        center: [55.788352966, 38.928768158],
        zoom: 16,
        searchControlProvider: "yandex#search"
    });

    // --- Старая метка с изображением ---
    var myPlacemark = new ymaps.Placemark(
        myMap.getCenter(),
        {
            hintContent: "Собственный значок метки",
            balloonContent: "Это красивая метка",
        },
        {
            iconLayout: "default#image",
            iconImageHref: "static/icons/mops.jpg",
            iconImageSize: [60, 60],
            iconImageOffset: [-5, -44],
        }
    );

    // --- Кастомный HTML маркер ---
    var CustomLayout = ymaps.templateLayoutFactory.createClass(
        '<div class="marker-class">Йоуу</div>'
    );

    var customMarker = new ymaps.Placemark(
        [55.788352966, 38.928768158],
        {},
        { iconLayout: CustomLayout, draggable: true }
    );

    // Добавляем все маркеры на карту
    myMap.geoObjects
        .add(myPlacemark)
        .add(myPlacemarkWithContent)
        .add(customMarker);
}

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

  fetch("/map", {
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

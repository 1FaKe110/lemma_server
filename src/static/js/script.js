function uploadFile() {
    var fileInput = document.getElementById("fileUpload");
    var file = fileInput.files[0];
    var formData = new FormData();
    console.log(file)
    formData.append("file", file);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.code == "error") {
            document.getElementById("statusInfo").innerText = "Статус обработки: Ошибка \n" + data.message;
        } else {
            data.code == "info"
            document.getElementById("statusInfo").innerText = "Статус: " + data.message;
            console.log(data)
            window.location.href = '/processing';
        }
    })
}

function DownloadServerFile(filename) {
    console.log("Downloading: " + filename);
    window.location.href = "/download/" + filename;
}

function operate(filename) {
    console.log("Запуск обработки файла: " + filename);
    fetch("/operate/" + filename, {
        method: "GET"
    })
    location.reload();
}

window.addEventListener('load', function () {
    document.body.classList.add('loaded');
});

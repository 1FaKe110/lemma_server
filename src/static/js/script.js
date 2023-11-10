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
        let statusInfo = document.getElementById("statusInfo")
        statusInfo.classList.add(data.code)
        if (data.code == "error") {
            statusInfo.innerText = "Статус обработки: Ошибка \n" + data.message;
        } else {
            statusInfo.innerText = "Статус: " + data.message;
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

function searchTable(tableId, searchInputId) {

    console.log(tableId)
    let table = document.getElementById(tableId);
    let searchInput = document.getElementById(searchInputId);
    let filter = searchInput.value.toUpperCase();
    let rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {
        let rowData = rows[i].getElementsByTagName("td");
        let foundMatch = false;

        for (let j = 0; j < rowData.length; j++) {
            console.log('rowData[j] = ' + rowData[j]);
            if (!rowData[j]) {
                continue;
            }

            input_tag = rowData[j].getElementsByClassName('name_column');
            console.log(input_tag);
            if (input_tag.length < 1) {
                continue;
            }
            var cellData = input_tag[0].value;


            console.log('cellData = ' + cellData)
            if (cellData.toUpperCase().indexOf(filter) > -1) {
//            if (cellData.toUpperCase() == filter.toUpperCase()) {
                foundMatch = true;
                break;
            }
        }

        rows[i].style.display = foundMatch ? "" : "none";
    }
}
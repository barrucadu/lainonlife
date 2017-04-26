// Messages to put in the title
var messages = [
    "THIS IS A 404",
    "THERE IS NOTHING HERE",
    "THE FILE IS NOT FOUND",
    "YOU HAVE TAKEN A WRONG TURN",
    "SOMEBODY FUCKED UP",
    "SHOUGANAI"
];
var current_message = 0;

function shuffle(array) {
    for(var i = array.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var temp = array[i];
        array[i] = array[j];
        array[j] = temp;
    }

    return array;
}

function change_message() {
    current_message ++;
    if(current_message == messages.length) {
        current_message = 0;
        messages = shuffle(messages);
    }

    document.getElementById("message").innerText = messages[current_message];
}

// Change the message regularly.
setInterval(change_message, 5000);

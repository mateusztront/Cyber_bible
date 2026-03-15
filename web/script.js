// Cyber Bible - Frontend Script

let isAdding = true;
const imageElements = [];

// Create post button
document.querySelector(".posts").onclick = async function() {
    const thedate = document.getElementById('input_date').value;
    const verse_break = document.getElementById('verse_break').value;

    console.log('Creating post for:', thedate, 'verse_break:', verse_break);

    try {
        const box = await eel.draw_post(thedate, verse_break)();
        console.log('Generated files:', box);

        const container = document.getElementById('images-container');

        if (isAdding) {
            for (let i = 1; i < box.length; i++) {
                const imageElement = document.createElement('img');
                imageElement.src = box[0] + box[i];
                imageElement.width = 400;
                imageElement.height = 400;
                imageElement.alt = box[i];
                container.appendChild(imageElement);
                imageElements.push(imageElement);
            }
        } else {
            // Remove all previously added elements
            imageElements.forEach(element => element.remove());
            imageElements.length = 0;
        }
        isAdding = !isAdding;
    } catch (error) {
        console.error('Error creating post:', error);
        alert('Error creating post. Check console for details.');
    }
}

// English readings button
document.querySelector(".english_readings").onclick = async function() {
    const thedate = document.getElementById('input_date').value;

    try {
        const content_list_text = await eel.readings_eng(thedate)();
        console.log('English readings:', content_list_text);

        const container = document.getElementById('content-container');

        for (let i = 0; i < content_list_text.length; i++) {
            const newDiv = document.createElement('div');
            const newContent = document.createTextNode(content_list_text[i]);
            newDiv.appendChild(newContent);
            container.appendChild(newDiv);
        }
    } catch (error) {
        console.error('Error fetching English readings:', error);
    }
}

// Polish readings button
document.querySelector(".polish_readings").onclick = async function() {
    const thedate = document.getElementById('input_date').value;

    try {
        const content_list_text = await eel.readings_pol(thedate)();

        const container = document.getElementById('content-container');
        const newDiv = document.createElement('div');

        const newTextArea = document.createElement('textarea');
        newTextArea.setAttribute("rows", "20");
        newTextArea.setAttribute("cols", "100");
        newTextArea.setAttribute("id", "dynamicTextArea");
        newTextArea.setAttribute("autocomplete", "off");

        for (let i = 0; i < content_list_text.length; i++) {
            const txt = document.createTextNode(content_list_text[i] + ' ');
            newTextArea.appendChild(txt);
        }

        newDiv.appendChild(newTextArea);
        container.appendChild(newDiv);
    } catch (error) {
        console.error('Error fetching Polish readings:', error);
    }
}

// Publish button
document.querySelector(".publish").onclick = async function() {
    const thedate = document.getElementById('input_date').value;
    const captionElement = document.getElementById('dynamicTextArea');
    const cap = captionElement ? captionElement.value : '';

    try {
        const publish_answer = await eel.publish(thedate, cap)();

        const container = document.getElementById('content-container');
        const newDiv = document.createElement('div');
        const newContent = document.createTextNode(
            publish_answer ? 'Published successfully!' : 'Publication failed'
        );
        newDiv.appendChild(newContent);
        container.appendChild(newDiv);
    } catch (error) {
        console.error('Error publishing:', error);
        alert('Error publishing. Check console for details.');
    }
}

// Set default date to today
document.addEventListener('DOMContentLoaded', function() {
    const d = new Date();
    const date_text = d.toLocaleDateString('en-CA');
    document.getElementById("input_date").value = date_text;
});

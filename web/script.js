// let thedate = document.querySelector("#input_date").value;
let isAdding = true;
const imageElements = [];

// Onclick of the button 
document.querySelector(".posts").onclick = async function() {   
      var thedate = document.getElementById('input_date').value;
      var verse_break = document.getElementById('verse_break').value;
      console.log(verse_break);
      const box = await eel.draw_post(thedate, verse_break)();
      // eel.draw_post()(path => console.log('Got this from Python: ' + path));
      // console.log($("#input_date").val());                    
      // !!!!!!!!!!!! add retured graphic to the html 
      console.log(box);
      if (isAdding) {
        for (let i = 1; i < box.length; i++) {
          imageElement = document.createElement('img'); 
          imageElement.src = box[0] + box[i]; 
          console.log(imageElement.src)
          imageElement.width="400";
          imageElement.height="400";
          document.body.appendChild(imageElement);  
          imageElements.push(imageElement);   
          }
        } else {
          // Remove all previously added elements
          imageElements.forEach(element => element.remove());
          imageElements.length = 0;
        }
        isAdding = !isAdding;
      }

document.querySelector(".english_readings").onclick = async function() {   
      var thedate = document.getElementById('input_date').value;
      const content_list_text = await eel.readings_eng(thedate)();
      // eel.draw_post()(path => console.log('Got this from Python: ' + path));
      // console.log(path);                    
      // !!!!!!!!!!!! add retured graphic to the html 
      console.log(content_list_text)
      for (let i = 0; i < content_list_text.length; i++) {
        newDiv  = document.createElement('div'); 
        newContent = document.createTextNode(content_list_text[i]);
        newDiv.appendChild(newContent);
        document.body.appendChild(newDiv);     
        }
      }

document.querySelector(".polish_readings").onclick = async function() {   
      var thedate = document.getElementById('input_date').value;
      const content_list_text = await eel.readings_pol(thedate)();
      // eel.draw_post()(path => console.log('Got this from Python: ' + path));
      // console.log(path);                    
      // !!!!!!!!!!!! add retured graphic to the html 
      console.log(content_list_text)
      for (let i = 0; i < content_list_text.length; i++) {
        newDiv  = document.createElement('div'); 
        newContent = document.createTextNode(content_list_text[i]);
        newDiv.appendChild(newContent);
        document.body.appendChild(newDiv);     
        }
      }

const d = new Date();
let date_text = d.toLocaleDateString('en-CA');
document.getElementById("input_date").value = date_text;


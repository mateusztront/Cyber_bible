

// Onclick of the button 
document.querySelector("button").onclick = async function() {   
  // TODO loop for each readings and pass list of reading to this loop
      // Call python's random_python function 
      const box = await eel.draw_text()();
      // eel.draw_text()(path => console.log('Got this from Python: ' + path));
      // console.log(path);                    
      // !!!!!!!!!!!! add retured graphic to the html 
      console.log(box)
      for (let i = 1; i < box.length; i++) {
        imageElement = document.createElement('img'); 
        imageElement.src = box[0] + box[i] + ".png"; 
        console.log(imageElement.src)
        imageElement.width="400";
        imageElement.height="400";
        document.body.appendChild(imageElement);     
        }
      }
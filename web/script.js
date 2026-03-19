// Cyber Bible - Frontend Script

let isAdding = true;
const imageElements = [];
let currentReadings = {};
let selectedReadingName = '';
let selectedReadingText = '';

// =============================================================================
// 2FA POPUP FUNCTIONS
// =============================================================================

// Poll for 2FA needed flag and show modal
let polling2FA = false;
let modal2FAShown = false;
let pollCount = 0;

async function poll2FANeeded() {
    if (polling2FA || modal2FAShown) return;

    // Check if eel is available
    if (typeof eel === 'undefined' || typeof eel.check_2fa_needed !== 'function') {
        return;
    }

    polling2FA = true;

    try {
        const needed = await eel.check_2fa_needed()();
        pollCount++;

        if (needed && !modal2FAShown) {
            console.log('2FA NEEDED! Showing modal now...');
            show2FAModal();
        }
    } catch (e) {
        // Silently ignore poll errors
    }

    polling2FA = false;
}

function show2FAModal() {
    modal2FAShown = true;
    const modal = document.getElementById('2fa-modal');
    const input = document.getElementById('2fa-code');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
        if (input) {
            input.value = '';
            input.focus();
        }
        console.log('Modal should now be visible');
    } else {
        console.error('Modal element not found!');
        // Fallback to prompt
        const code = prompt('Instagram wymaga kodu 2FA.\nWprowadź 6-cyfrowy kod:');
        if (code && code.trim().length >= 6) {
            eel.submit_2fa_code(code.trim());
        } else {
            eel.submit_2fa_code('');
        }
        modal2FAShown = false;
    }
}

function hide2FAModal() {
    modal2FAShown = false;
    const modal = document.getElementById('2fa-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

// 2FA modal event handlers - set up when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const submitBtn = document.getElementById('2fa-submit');
    const cancelBtn = document.getElementById('2fa-cancel');
    const codeInput = document.getElementById('2fa-code');

    if (submitBtn) {
        submitBtn.onclick = function() {
            const code = codeInput.value.trim();
            console.log('Submitting 2FA code:', code);
            if (code.length >= 6) {
                eel.submit_2fa_code(code);
                hide2FAModal();
            } else {
                alert('Kod musi mieć co najmniej 6 znaków');
            }
        };
    }

    if (cancelBtn) {
        cancelBtn.onclick = function() {
            console.log('2FA cancelled');
            eel.submit_2fa_code('');
            hide2FAModal();
        };
    }

    if (codeInput) {
        codeInput.onkeypress = function(e) {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        };
    }

});

// Start polling when page loads
setInterval(poll2FANeeded, 500);

// =============================================================================
// COVER GENERATION FUNCTIONS
// =============================================================================

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('cover-status');
    statusDiv.innerHTML = `<div class="status-message ${type}">${message}</div>`;
}

function showLoading(message) {
    const statusDiv = document.getElementById('cover-status');
    statusDiv.innerHTML = `<div class="status-message info"><span class="spinner"></span>${message}</div>`;
}

function clearStatus() {
    document.getElementById('cover-status').innerHTML = '';
}

// =============================================================================
// READING DISPLAY FUNCTIONS
// =============================================================================

function createReadingTabs(readings) {
    const tabsContainer = document.getElementById('reading-tabs');
    tabsContainer.innerHTML = '';

    const readingNames = Object.keys(readings);

    readingNames.forEach((name, index) => {
        const tab = document.createElement('div');
        tab.className = 'reading-tab';
        tab.textContent = name;
        tab.onclick = () => displayReading(name);
        tabsContainer.appendChild(tab);
    });

    // Show first reading by default
    if (readingNames.length > 0) {
        displayReading(readingNames[0]);
    }
}

async function displayReading(readingName) {
    const thedate = document.getElementById('input_date').value;

    // Update tab active state
    document.querySelectorAll('.reading-tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent === readingName);
    });

    // Show content area
    document.getElementById('reading-content-area').style.display = 'block';
    document.getElementById('reading-type').textContent = readingName;
    document.getElementById('reading-text').innerHTML = '<span class="reading-placeholder">Loading...</span>';

    try {
        const fullText = await eel.get_full_reading_text(thedate, readingName)();

        // Parse reference from first line if present
        const lines = fullText.split('\n');
        let reference = '';
        let textContent = fullText;

        if (lines.length > 0 && lines[0].match(/^[A-Za-z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]+\d/)) {
            reference = lines[0];
            textContent = lines.slice(1).join('\n');
        }

        document.getElementById('reading-reference').textContent = reference;

        // Format text with paragraphs
        const paragraphs = textContent.split('\n').filter(p => p.trim());
        const formattedText = paragraphs.map(p => `<p>${p}</p>`).join('');
        document.getElementById('reading-text').innerHTML = formattedText || '<span class="reading-placeholder">No content</span>';

    } catch (error) {
        console.error('Error loading reading:', error);
        document.getElementById('reading-text').innerHTML = '<span class="reading-placeholder">Error loading reading</span>';
    }
}

// Load readings for cover generation
document.getElementById('load-readings-btn').onclick = async function() {
    const thedate = document.getElementById('input_date').value;

    if (!thedate) {
        showStatus('Please select a date first.', 'warning');
        return;
    }

    showLoading('Loading readings...');

    try {
        // Check if cover already exists
        const coverExists = await eel.check_cover_exists(thedate)();
        if (coverExists) {
            showStatus('Cover already exists for this date. You can regenerate if needed.', 'warning');
            document.getElementById('cover-preview').src = `/${thedate}/mateusztront.jpg?t=${Date.now()}`;
            document.getElementById('cover-preview').style.display = 'block';
        }

        currentReadings = await eel.get_readings_for_cover(thedate)();

        const select = document.getElementById('reading-select');
        select.innerHTML = '<option value="">-- Select a reading --</option>';

        for (const [name, preview] of Object.entries(currentReadings)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = `${name}: ${preview.substring(0, 60)}...`;
            select.appendChild(option);
        }

        select.disabled = false;
        document.getElementById('generate-prompt-btn').disabled = false;
        document.getElementById('generate-variations-btn').disabled = false;

        // Create reading tabs and display first reading
        createReadingTabs(currentReadings);

        if (!coverExists) {
            showStatus('Readings loaded. Select one to generate cover prompt.', 'success');
        }

    } catch (error) {
        console.error('Error loading readings:', error);
        showStatus('Error loading readings. Check console for details.', 'error');
    }
};

// Handle reading selection - load English text into prompt
document.getElementById('reading-select').onchange = async function() {
    selectedReadingName = this.value;

    if (!selectedReadingName) {
        selectedReadingText = '';
        return;
    }

    const thedate = document.getElementById('input_date').value;
    showLoading('Loading English reading from Bible API...');

    try {
        // Get Polish reading for display
        selectedReadingText = await eel.get_full_reading_text(thedate, selectedReadingName)();

        // Get English reading text using Bible API (based on Polish reference)
        const englishText = await eel.get_english_reading_text(thedate, selectedReadingName)();

        if (englishText && !englishText.startsWith('Error') && !englishText.startsWith('Could not')) {
            document.getElementById('midjourney-prompt').value = englishText + ' --ar 1:1';
            document.getElementById('generate-cover-btn').disabled = false;
            showStatus(`Selected: ${selectedReadingName} - English text loaded for editing`, 'success');
        } else {
            document.getElementById('midjourney-prompt').value = '';
            showStatus(`${selectedReadingName}: ${englishText}`, 'warning');
        }
    } catch (error) {
        console.error('Error getting reading text:', error);
        showStatus('Error loading reading text', 'error');
    }
};

// Generate single prompt
document.getElementById('generate-prompt-btn').onclick = async function() {
    if (!selectedReadingName || !selectedReadingText) {
        showStatus('Please select a reading first.', 'warning');
        return;
    }

    showLoading('Generating prompt with AI...');
    document.getElementById('prompt-variations-container').style.display = 'none';

    try {
        const prompt = await eel.generate_cover_prompt(selectedReadingText, selectedReadingName)();

        document.getElementById('midjourney-prompt').value = prompt;
        document.getElementById('generate-cover-btn').disabled = false;

        showStatus('Prompt generated! Edit if needed, then click Generate Cover.', 'success');

    } catch (error) {
        console.error('Error generating prompt:', error);
        showStatus('Error generating prompt. Check console for details.', 'error');
    }
};

// Generate multiple prompt variations
document.getElementById('generate-variations-btn').onclick = async function() {
    if (!selectedReadingName || !selectedReadingText) {
        showStatus('Please select a reading first.', 'warning');
        return;
    }

    showLoading('Generating 3 prompt variations with AI...');

    try {
        const variations = await eel.generate_cover_prompt_variations(selectedReadingText, selectedReadingName, 3)();

        const container = document.getElementById('prompt-variations-container');
        container.innerHTML = '<p><strong>Click a variation to use it:</strong></p>';
        container.style.display = 'flex';

        variations.forEach((prompt, index) => {
            const div = document.createElement('div');
            div.className = 'prompt-variation';
            div.textContent = `${index + 1}. ${prompt}`;
            div.onclick = function() {
                // Remove selected class from all
                container.querySelectorAll('.prompt-variation').forEach(el => el.classList.remove('selected'));
                // Add to this one
                div.classList.add('selected');
                // Set the prompt
                document.getElementById('midjourney-prompt').value = prompt;
                document.getElementById('generate-cover-btn').disabled = false;
            };
            container.appendChild(div);
        });

        showStatus('Click a variation to use it, or edit directly.', 'success');

    } catch (error) {
        console.error('Error generating variations:', error);
        showStatus('Error generating variations. Check console for details.', 'error');
    }
};

// Grid selection state
let currentGridData = null;

// Generate cover grid (shows 4 images for selection)
document.getElementById('generate-cover-btn').onclick = async function() {
    const thedate = document.getElementById('input_date').value;
    const prompt = document.getElementById('midjourney-prompt').value.trim();

    if (!thedate) {
        showStatus('Please select a date first.', 'warning');
        return;
    }

    if (!prompt) {
        showStatus('Please generate or enter a prompt first.', 'warning');
        return;
    }

    // Disable button during generation
    this.disabled = true;
    showLoading('Generating 4 image options via Midjourney... This may take 1-2 minutes.');

    // Hide previous results
    document.getElementById('grid-preview-container').style.display = 'none';
    document.getElementById('cover-preview').style.display = 'none';

    try {
        const result = await eel.generate_cover_grid(thedate, prompt)();

        if (result.error) {
            showStatus('Error: ' + result.error, 'error');
            this.disabled = false;
            return;
        }

        // Store grid data for upscale
        currentGridData = {
            messageId: result.message_id,
            buttons: result.buttons,
            thedate: thedate
        };

        // Show the grid
        document.getElementById('grid-image').src = result.grid_url;
        document.getElementById('grid-preview-container').style.display = 'block';

        showStatus('Click on the image (1-4) you want to use as cover.', 'success');
        this.disabled = false;

    } catch (error) {
        console.error('Error generating grid:', error);
        showStatus('Error generating grid. Check console for details.', 'error');
        this.disabled = false;
    }
};

// Handle grid quadrant clicks
document.querySelectorAll('.grid-quadrant').forEach(quadrant => {
    quadrant.onclick = async function() {
        if (!currentGridData) {
            showStatus('No grid data. Generate a grid first.', 'warning');
            return;
        }

        const variant = this.dataset.variant;
        const customId = currentGridData.buttons[variant];

        if (!customId) {
            showStatus('Button data not found for ' + variant, 'error');
            return;
        }

        showLoading('Upscaling selected image...');

        try {
            const result = await eel.upscale_cover(
                currentGridData.thedate,
                currentGridData.messageId,
                customId
            )();

            if (result.startsWith('Error:')) {
                showStatus(result, 'error');
                return;
            }

            // Hide grid, show final cover
            document.getElementById('grid-preview-container').style.display = 'none';
            document.getElementById('cover-preview').src = result + '?t=' + Date.now();
            document.getElementById('cover-preview').style.display = 'block';

            showStatus('Cover image saved!', 'success');
            currentGridData = null;

        } catch (error) {
            console.error('Error upscaling:', error);
            showStatus('Error upscaling. Check console for details.', 'error');
        }
    };
});

// =============================================================================
// EXISTING FUNCTIONS
// =============================================================================

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

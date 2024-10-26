const dropArea = document.getElementById('drop-area');
const fileElem = document.getElementById('fileElem');
const chatWindow = document.getElementById('file-info');  // Displays uploaded files
const generatedNotes = document.getElementById('generated-notes');  // Displays notes
const spinner = document.getElementById('loading-spinner');

const MAX_FILE_SIZE_MB = 200;
let isProcessing = false;
const uploadedFiles = new Set();

// Drag and drop events
dropArea.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropArea.classList.add('drag-over');
});

dropArea.addEventListener('dragleave', () => {
    dropArea.classList.remove('drag-over');
});

dropArea.addEventListener('drop', async (event) => {
    event.preventDefault();
    dropArea.classList.remove('drag-over');
    const files = Array.from(event.dataTransfer.files);
    await handleFiles(files);
});

dropArea.addEventListener('click', () => fileElem.click());

fileElem.addEventListener('change', async (event) => {
    const files = Array.from(event.target.files);
    await handleFiles(files);
    fileElem.value = '';  // Clear input
});

async function handleFiles(files) {
    if (isProcessing) return;
    isProcessing = true;

    for (const file of files) {
        if (uploadedFiles.has(file.name)) {
            alert(`${file.name} already processed.`);
            continue;
        }

        uploadedFiles.add(file.name);

        if (file.size / (1024 * 1024) > MAX_FILE_SIZE_MB) {
            alert(`${file.name} exceeds the size limit.`);
        } else {
            displayFileMessage(file);
            const transcription = await transcribeAudio(file);
            if (transcription) {
                const notes = await generateNotes(transcription);
                displayNotes(notes);
            }
        }
    }

    isProcessing = false;
}

function displayFileMessage(file) {
    chatWindow.innerHTML = `<p>${file.name} (${(file.size / 1024).toFixed(2)} KB) uploaded.</p>`;
}

async function transcribeAudio(file) {
    try {
        showSpinner();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error('Transcription failed.');
        const data = await response.json();
        return data.transcription;
    } catch (error) {
        console.error('Transcription Error:', error);
        alert('Error during transcription.');
    } finally {
        hideSpinner();
    }
}

async function generateNotes(transcription) {
    try {
        const response = await fetch('/generate-notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcription }),
        });

        if (!response.ok) throw new Error('Notes generation failed.');
        const data = await response.json();
        return data.notes;
    } catch (error) {
        console.error('Notes Generation Error:', error);
        alert('Error generating notes.');
    }
}

function displayNotes(notes) {
    const message = document.createElement('div');
    message.classList.add('message', 'alert', 'alert-success', 'fade-in');  // Add fade-in effect

    const formattedNotes = marked(notes.trim());  // Format the notes dynamically
    message.innerHTML = `<strong>Generated Notes:</strong><br>${formattedNotes}`;

    generatedNotes.appendChild(message);
    generatedNotes.scrollTop = generatedNotes.scrollHeight;  // Auto-scroll to the bottom
}

// Helper function to format notes like ChatGPT
function formatNotes(notes) {
    let formatted = '';
    const lines = notes.split('\n');  // Split response into lines

    lines.forEach(line => {
        if (line.startsWith('#')) {
            formatted += `<h3>${line.replace(/#/g, '').trim()}</h3>`;
        } else if (line.startsWith('-') || line.startsWith('*')) {
            formatted += `<li>${line.replace(/[-*]/, '').trim()}</li>`;
        } else if (/^\d+\./.test(line)) {
            formatted += `<li>${line.trim()}</li>`;
        } else {
            formatted += `<p>${line.trim()}</p>`;
        }
    });

    formatted = formatted.replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>');  // Wrap list items in <ul>
    return formatted;
}


function showSpinner() {
    spinner.style.display = 'inline-block';
}

function hideSpinner() {
    spinner.style.display = 'none';
}

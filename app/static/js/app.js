document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('reviewForm');
    const loader = document.getElementById('loader');
    const result = document.getElementById('result');
    const errorMessage = document.getElementById('errorMessage');
    const submitBtn = document.getElementById('submitBtn');
    const reviewSection = document.getElementById('reviewSection');
    const refactoredSection = document.getElementById('refactoredSection');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Reset UI
        loader.style.display = 'block';
        result.style.display = 'none';
        errorMessage.style.display = 'none';
        submitBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('file', document.getElementById('file').files[0]);
        formData.append('language', document.getElementById('language').value);
        
        const includeRefactored = document.getElementById('includeRefactored').checked;
        const endpoint = includeRefactored ? '/api/v1/review-and-refactor' : '/api/v1/review';
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to analyze code');
            }
            
            const data = await response.json();
            displayResults(data, includeRefactored);
        } catch (error) {
            errorMessage.textContent = error.message;
            errorMessage.style.display = 'block';
            console.error('Error:', error);
        } finally {
            loader.style.display = 'none';
            submitBtn.disabled = false;
        }
    });
    
    function displayResults(data, includeRefactored) {
        // Review section
        let reviewHTML = `
            <div class="bg-white p-4 rounded-lg border-l-4 border-blue-500 mb-4">
                <div class="inline-block bg-gradient-to-r from-blue-500 to-blue-700 text-white px-4 py-2 rounded font-bold">
                    Rating: ${data.rating}/10
                </div>
            </div>
            
            <div class="bg-white p-4 rounded-lg border-l-4 border-blue-500 mb-4">
                <h3 class="text-lg font-bold text-gray-800 mb-3">Summary</h3>
                <p class="text-gray-700 leading-relaxed">${escapeHtml(data.summary)}</p>
            </div>
        `;
        
        // Issues
        if (data.issues && data.issues.length > 0) {
            reviewHTML += '<div class="bg-white p-4 rounded-lg border-l-4 border-blue-500 mb-4"><h3 class="text-lg font-bold text-gray-800 mb-3">Issues Found</h3>';
            data.issues.forEach(issue => {
                const severityColor = {
                    'info': 'border-blue-400 bg-blue-50',
                    'warning': 'border-yellow-400 bg-yellow-50',
                    'error': 'border-red-400 bg-red-50'
                }[issue.severity] || 'border-yellow-400 bg-yellow-50';
                
                reviewHTML += `
                    <div class="border-l-4 p-3 mb-3 rounded ${severityColor}">
                        <div class="font-bold text-gray-800">Line ${issue.line} - ${issue.severity.toUpperCase()}</div>
                        <div class="text-gray-700 text-sm mt-1">${escapeHtml(issue.description)}</div>
                    </div>
                `;
            });
            reviewHTML += '</div>';
        } else {
            reviewHTML += '<div class="bg-white p-4 rounded-lg border-l-4 border-green-500 mb-4"><div class="text-green-700 font-bold">✓ No issues found!</div></div>';
        }
        
        reviewSection.innerHTML = reviewHTML;
        
        // Refactored section
        if (includeRefactored && data.refactored_code) {
            let refactoredHTML = '<div class="bg-white p-4 rounded-lg border-l-4 border-blue-500 mb-4">';
            refactoredHTML += '<div class="flex justify-between items-center mb-3">';
            refactoredHTML += '<h3 class="text-lg font-bold text-gray-800">Refactored Code</h3>';
            refactoredHTML += '<button class="copy-btn bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded font-bold transition" id="copyBtn" type="button">Copy Code</button>';
            refactoredHTML += '</div>';
            refactoredHTML += `<pre class="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto font-mono text-sm leading-relaxed max-h-96 overflow-y-auto" id="refactoredCode"><code>${escapeHtml(data.refactored_code)}</code></pre>`;
            refactoredHTML += '</div>';
            
            // Changes
            if (data.changes_made && data.changes_made.length > 0) {
                refactoredHTML += '<div class="bg-white p-4 rounded-lg border-l-4 border-blue-500 mb-4">';
                refactoredHTML += '<h3 class="text-lg font-bold text-gray-800 mb-3">Changes Made</h3>';
                refactoredHTML += '<div class="bg-blue-50 p-4 rounded border-l-4 border-blue-400"><ul class="list-none">';
                data.changes_made.forEach(change => {
                    refactoredHTML += `<li class="py-2 text-gray-700 border-b border-blue-200 last:border-b-0"><span class="text-blue-500 font-bold">✓</span> ${escapeHtml(change)}</li>`;
                });
                refactoredHTML += '</ul></div></div>';
            }
            
            refactoredSection.innerHTML = refactoredHTML;
            
            // Add copy button handler
            const copyBtn = document.getElementById('copyBtn');
            if (copyBtn) {
                copyBtn.addEventListener('click', async () => {
                    try {
                        await navigator.clipboard.writeText(data.refactored_code);
                        copyBtn.textContent = 'Copied!';
                        copyBtn.classList.remove('bg-blue-500', 'hover:bg-blue-700');
                        copyBtn.classList.add('bg-green-500');
                        setTimeout(() => {
                            copyBtn.textContent = 'Copy Code';
                            copyBtn.classList.remove('bg-green-500');
                            copyBtn.classList.add('bg-blue-500', 'hover:bg-blue-700');
                        }, 1500);
                    } catch (err) {
                        copyBtn.textContent = 'Copy failed';
                        setTimeout(() => (copyBtn.textContent = 'Copy Code'), 1500);
                    }
                });
            }
            
            // Highlight code if Highlight.js is available
            if (window.hljs) {
                const codeBlock = document.getElementById('refactoredCode');
                hljs.highlightElement(codeBlock);
            }
        } else {
            refactoredSection.innerHTML = '';
        }
        
        result.style.display = 'block';
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

def build_file_input_js() -> str:
    return """
            (function() {
                // Find any file input elements on the page
                const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
                
                // Make the first file input visible and interactive
                if (fileInputs.length > 0) {
                    fileInputs[0].style.opacity = '1';
                    fileInputs[0].style.display = 'block';
                    fileInputs[0].style.visibility = 'visible';
                    fileInputs[0].style.position = 'relative';
                    fileInputs[0].removeAttribute('hidden');
                    return true;
                }
                return false;
            })();
            """

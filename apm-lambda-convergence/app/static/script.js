document.addEventListener('DOMContentLoaded', function () {
    const successBtn = document.getElementById('successBtn');
    const errorBtn = document.getElementById('errorBtn');
    const responseEl = document.getElementById('response');
    const loaderEl = document.getElementById('loader');

    const invokeLambda = async (action) => {
        responseEl.textContent = '';
        loaderEl.style.display = 'block';

        try {
            const response = await fetch('/invoke-lambda', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: action }),
            });

            const result = await response.json();
            
            responseEl.textContent = JSON.stringify(result, null, 2);
            
            if (!response.ok) {
                responseEl.style.color = '#ef4444'; // Red text for errors
            } else {
                responseEl.style.color = '#f0fdf4'; // Default text color
            }

        } catch (error) {
            console.error('Error invoking Lambda:', error);
            responseEl.textContent = `An error occurred: ${error.message}`;
            responseEl.style.color = '#ef4444';
        } finally {
            loaderEl.style.display = 'none';
        }
    };

    successBtn.addEventListener('click', () => invokeLambda('success'));
    errorBtn.addEventListener('click', () => invokeLambda('error'));
});
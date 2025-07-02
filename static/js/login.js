$(document).ready(function() {
    const $form = $('#login-form');
    const $submitBtn = $('#submit-btn');
    const $btnText = $('#btn-text');
    const $btnLoading = $('#btn-loading');
    const $errorMessage = $('#error-message');
    const $errorText = $('#error-text');
    const $username = $('#username');
    const $password = $('#password');
    
    // Hide error message
    function hideMessages() {
        $errorMessage.addClass('hidden');
    }
    
    // Show error message
    function showError(message) {
        hideMessages();
        
        if (typeof message === 'string') {
            $errorText.html(message);
        } else if (typeof message === 'object') {
            let errorHtml = '<ul class="list-disc list-inside">';
            $.each(message, function(field, messages) {
                if (Array.isArray(messages)) {
                    $.each(messages, function(index, msg) {
                        errorHtml += `<li><strong>${field}:</strong> ${msg}</li>`;
                    });
                } else {
                    errorHtml += `<li><strong>${field}:</strong> ${messages}</li>`;
                }
            });
            errorHtml += '</ul>';
            $errorText.html(errorHtml);
        }
        
        $errorMessage.removeClass('hidden');
        $errorMessage[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Toggle loading state
    function setLoading(loading) {
        $submitBtn.prop('disabled', loading);
        if (loading) {
            $btnText.addClass('hidden');
            $btnLoading.removeClass('hidden');
        } else {
            $btnText.removeClass('hidden');
            $btnLoading.addClass('hidden');
        }
    }
    
    // Check if user is already logged in
    function checkExistingToken() {
        const accessToken = localStorage.getItem('accessToken');
        if (accessToken) {
            // Optional: Verify token validity with a quick API call
            // For now, just redirect if token exists
            console.log('User already has a token, redirecting to dashboard...');
            // window.location.href = '/dashboard/';
        }
    }
    
    // Save tokens to localStorage
    function saveTokens(accessToken, refreshToken) {
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        console.log('Tokens saved successfully');
    }
    
    // Redirect to dashboard
    function redirectToDashboard() {
        console.log('Redirecting to dashboard...');
        // Replace with your actual dashboard URL
        window.location.href = '/dashboard/';
        
        // For now, show a success message since dashboard doesn't exist yet
        setTimeout(function() {
            alert('Login successful! Tokens saved to localStorage.\n\nRedirect to dashboard would happen here.');
        }, 100);
    }
    
    // Check for existing token on page load
    checkExistingToken();
    
    // Form submission handler
    $form.on('submit', function(e) {
        e.preventDefault();
        
        hideMessages();
        setLoading(true);
        
        const formData = {
            username: $username.val().trim(),
            password: $password.val()
        };
        
        // Basic client-side validation
        if (!formData.username || !formData.password) {
            showError('Please enter both username and password');
            setLoading(false);
            return;
        }
        
        // Get CSRF token
        const csrfToken = $('[name=csrfmiddlewaretoken]').val() || '';
        
        $.ajax({
            url: '/api/v1/token/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            headers: {
                'X-CSRFToken': csrfToken
            },
            success: function(data, textStatus, xhr) {
                console.log('Login successful:', data);
                
                // Check if we received the expected tokens
                if (data.access && data.refresh) {
                    saveTokens(data.access, data.refresh);
                    redirectToDashboard();
                } else {
                    showError('Invalid response from server. Please try again.');
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error('Login error:', xhr.responseJSON);
                
                if (xhr.status === 401) {
                    showError('Invalid username or password. Please try again.');
                } else if (xhr.responseJSON) {
                    // Handle specific API errors
                    const errorMsg = xhr.responseJSON.detail || 
                                    xhr.responseJSON.error || 
                                    xhr.responseJSON.message ||
                                    'Login failed. Please try again.';
                    showError(errorMsg);
                } else if (xhr.status >= 500) {
                    showError('Server error. Please try again later.');
                } else {
                    showError('Network error. Please check your connection and try again.');
                }
            },
            complete: function() {
                setLoading(false);
            }
        });
    });
    
    // Enter key handler for better UX
    $username.add($password).on('keypress', function(e) {
        if (e.which === 13) { // Enter key
            $form.submit();
        }
    });
    
    // Clear error message when user starts typing
    $username.add($password).on('input', function() {
        hideMessages();
    });
});

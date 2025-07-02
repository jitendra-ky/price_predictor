$(document).ready(function() {
    const $form = $('#register-form');
    const $submitBtn = $('#submit-btn');
    const $btnText = $('#btn-text');
    const $btnLoading = $('#btn-loading');
    const $successMessage = $('#success-message');
    const $errorMessage = $('#error-message');
    const $errorText = $('#error-text');
    const $password = $('#password');
    const $confirmPassword = $('#confirm_password');
    
    // Hide messages
    function hideMessages() {
        $successMessage.addClass('hidden');
        $errorMessage.addClass('hidden');
    }
    
    // Show success message
    function showSuccess(message) {
        hideMessages();
        $('#success-text').text(message);
        $successMessage.removeClass('hidden');
        $successMessage[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Show error message
    function showError(errors) {
        hideMessages();
        
        if (typeof errors === 'string') {
            $errorText.html(errors);
        } else if (typeof errors === 'object') {
            let errorHtml = '<ul class="list-disc list-inside">';
            $.each(errors, function(field, messages) {
                if (Array.isArray(messages)) {
                    $.each(messages, function(index, message) {
                        errorHtml += `<li><strong>${field}:</strong> ${message}</li>`;
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
    
    // Validate passwords match
    function validatePasswords() {
        const password = $password.val();
        const confirmPassword = $confirmPassword.val();
        
        if (confirmPassword && password !== confirmPassword) {
            showError('Passwords do not match');
            return false;
        }
        return true;
    }
    
    // Add real-time password validation
    $confirmPassword.on('blur', validatePasswords);
    
    // Form submission handler
    $form.on('submit', function(e) {
        e.preventDefault();
        
        // Validate passwords match
        if (!validatePasswords()) {
            return;
        }
        
        hideMessages();
        setLoading(true);
        
        const formData = {
            username: $('#username').val(),
            email: $('#email').val(),
            password: $password.val()
        };
        
        // Get CSRF token
        const csrfToken = $('[name=csrfmiddlewaretoken]').val() || '';
        
        $.ajax({
            url: '/api/v1/register/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            headers: {
                'X-CSRFToken': csrfToken
            },
            success: function(data, textStatus, xhr) {
                showSuccess('Account created successfully! You can now sign in.');
                $form[0].reset();
                
                // Optional: Redirect to login page after 3 seconds
                setTimeout(function() {
                    // window.location.href = '/login/';
                }, 3000);
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error('Registration error:', xhr.responseJSON);
                
                if (xhr.responseJSON) {
                    showError(xhr.responseJSON.errors || xhr.responseJSON.error || 'Registration failed');
                } else {
                    showError('Network error. Please try again.');
                }
            },
            complete: function() {
                setLoading(false);
            }
        });
    });
});

$(document).ready(function() {
    // jQuery element references
    const $form = $('#prediction-form');
    const $tickerInput = $('#ticker-input');
    const $predictBtn = $('#predict-btn');
    const $predictBtnText = $('#predict-btn-text');
    const $predictBtnLoading = $('#predict-btn-loading');
    const $logoutBtn = $('#logout-btn');
    
    // Message elements
    const $messageContainer = $('#message-container');
    const $successMessage = $('#success-message');
    const $errorMessage = $('#error-message');
    const $successText = $('#success-text');
    const $errorText = $('#error-text');
    
    // Result elements
    const $predictedPrice = $('#predicted-price');
    const $tickerSymbol = $('#ticker-symbol');
    const $historyChart = $('#history-chart');
    const $predictionChart = $('#prediction-chart');
    const $historyPlaceholder = $('#history-placeholder');
    const $predictionPlaceholder = $('#prediction-placeholder');
    const $mseValue = $('#mse-value');
    const $rmseValue = $('#rmse-value');
    const $r2Value = $('#r2-value');
    
    // Table elements
    const $predictionsTableBody = $('#predictions-table-body');
    
    // Authentication check
    function checkAuthentication() {
        const accessToken = localStorage.getItem('accessToken');
        if (!accessToken) {
            window.location.href = '/login/';
            return false;
        }
        return true;
    }
    
    // Hide all messages
    function hideMessages() {
        $messageContainer.addClass('hidden');
        $successMessage.addClass('hidden');
        $errorMessage.addClass('hidden');
    }
    
    // Show success message
    function showSuccess(message) {
        hideMessages();
        $successText.text(message);
        $successMessage.removeClass('hidden');
        $messageContainer.removeClass('hidden');
        $messageContainer[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
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
        $messageContainer.removeClass('hidden');
        $messageContainer[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Toggle loading state
    function setLoading(loading) {
        $predictBtn.prop('disabled', loading);
        if (loading) {
            $predictBtnText.addClass('hidden');
            $predictBtnLoading.removeClass('hidden');
        } else {
            $predictBtnText.removeClass('hidden');
            $predictBtnLoading.addClass('hidden');
        }
    }
    
    // Update prediction results
    function updateResults(data) {
        console.log('Updating results with data:', data);
        
        // Check if data has metrics nested object or direct properties
        const metrics = data.metrics || data;
        
        // Update predicted price
        const nextDayPrice = metrics.next_day_price || data.next_day_price;
        if (nextDayPrice) {
            $predictedPrice.html(`$${parseFloat(nextDayPrice).toFixed(2)}`);
        }
        
        // Update ticker symbol
        const ticker = data.ticker || 'Unknown';
        $tickerSymbol.text(`${ticker.toUpperCase()} - Next Day Prediction`);
        
        // Update metrics with proper fallbacks
        const mse = metrics.mse || data.mse;
        const rmse = metrics.rmse || data.rmse;
        const r2 = metrics.r2 || data.r2;
        
        $mseValue.text(mse ? parseFloat(mse).toFixed(4) : '--');
        $rmseValue.text(rmse ? parseFloat(rmse).toFixed(4) : '--');
        $r2Value.text(r2 ? parseFloat(r2).toFixed(4) : '--');
        
        // Update charts if plot URLs are provided
        if (data.plot_urls && Array.isArray(data.plot_urls) && data.plot_urls.length >= 2) {
            console.log('Loading charts:', data.plot_urls);
            
            // Show history chart
            $historyChart.attr('src', data.plot_urls[0]).removeClass('hidden');
            $historyPlaceholder.addClass('hidden');
            
            // Show prediction chart  
            $predictionChart.attr('src', data.plot_urls[1]).removeClass('hidden');
            $predictionPlaceholder.addClass('hidden');
            
            // Handle image load errors
            $historyChart.off('error').on('error', function() {
                console.error('Failed to load history chart:', data.plot_urls[0]);
                $(this).addClass('hidden');
                $historyPlaceholder.removeClass('hidden');
            });
            
            $predictionChart.off('error').on('error', function() {
                console.error('Failed to load prediction chart:', data.plot_urls[1]);
                $(this).addClass('hidden');
                $predictionPlaceholder.removeClass('hidden');
            });
            
            // Add load success handlers for better debugging
            $historyChart.off('load').on('load', function() {
                console.log('History chart loaded successfully');
            });
            
            $predictionChart.off('load').on('load', function() {
                console.log('Prediction chart loaded successfully');
            });
        } else {
            console.warn('No plot URLs found or insufficient charts in response');
        }
    }
    
    // Reset results to default state
    function resetResults() {
        $predictedPrice.html('<span class="text-gray-400">--</span>');
        $tickerSymbol.text('Select a ticker to get prediction');
        $mseValue.text('--');
        $rmseValue.text('--');
        $r2Value.text('--');
        
        // Hide charts and show placeholders
        $historyChart.addClass('hidden').attr('src', '');
        $predictionChart.addClass('hidden').attr('src', '');
        $historyPlaceholder.removeClass('hidden');
        $predictionPlaceholder.removeClass('hidden');
    }
    
    // Load prediction history
    function loadPredictionHistory() {
        const accessToken = localStorage.getItem('accessToken');
        if (!accessToken) {
            return;
        }
        
        $.ajax({
            url: '/api/v1/predictions/',
            type: 'GET',
            headers: {
                'Authorization': `Bearer ${accessToken}`
            },
            success: function(data, textStatus, xhr) {
                console.log('Prediction history loaded:', data);
                populatePredictionTable(data);
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error('Failed to load prediction history:', xhr.responseJSON);
                
                if (xhr.status === 401) {
                    // Token expired or invalid
                    localStorage.removeItem('accessToken');
                    localStorage.removeItem('refreshToken');
                    window.location.href = '/login/';
                } else {
                    showError('Failed to load prediction history. Please refresh the page.');
                }
            }
        });
    }
    
    // Populate prediction table
    function populatePredictionTable(predictions) {
        // Clear existing table content
        $predictionsTableBody.empty();
        
        if (!predictions || predictions.length === 0) {
            // Show empty state
            const emptyRow = `
                <tr>
                    <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                        <div class="flex flex-col items-center">
                            <svg class="h-12 w-12 mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
                            </svg>
                            <p>No predictions yet. Make your first prediction above!</p>
                        </div>
                    </td>
                </tr>
            `;
            $predictionsTableBody.append(emptyRow);
            return;
        }
        
        // Populate table with prediction data
        predictions.forEach(function(prediction, index) {
            const metrics = prediction.metrics || {};
            
            // Format date
            const createdDate = new Date(prediction.created);
            const formattedDate = createdDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            
            // Format values with fallbacks
            const nextDayPrice = metrics.next_day_price ? `$${parseFloat(metrics.next_day_price).toFixed(2)}` : '--';
            const mse = metrics.mse ? parseFloat(metrics.mse).toFixed(4) : '--';
            const rmse = metrics.rmse ? parseFloat(metrics.rmse).toFixed(4) : '--';
            const r2 = metrics.r2 ? parseFloat(metrics.r2).toFixed(4) : '--';
            
            // Alternate row colors for better readability
            const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
            
            const row = `
                <tr class="${rowClass} hover:bg-gray-100 transition-colors duration-150">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        ${prediction.ticker || '--'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${formattedDate}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">
                        ${nextDayPrice}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${mse}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${rmse}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${r2}
                    </td>
                </tr>
            `;
            
            $predictionsTableBody.append(row);
        });
        
        console.log(`Populated table with ${predictions.length} predictions`);
    }
    
    // Logout functionality
    $logoutBtn.on('click', function() {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login/';
    });
    
    // Form submission handler
    $form.on('submit', function(e) {
        e.preventDefault();
        
        // Check authentication
        if (!checkAuthentication()) {
            return;
        }
        
        const ticker = $tickerInput.val().trim().toUpperCase();
        
        // Basic validation
        if (!ticker) {
            showError('Please enter a stock ticker symbol');
            return;
        }
        
        hideMessages();
        setLoading(true);
        resetResults();
        
        const accessToken = localStorage.getItem('accessToken');
        
        $.ajax({
            url: '/api/v1/predict/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ticker: ticker }),
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val() || ''
            },
            success: function(data, textStatus, xhr) {
                console.log('Prediction successful:', data);
                updateResults(data);
                showSuccess(`Prediction completed successfully for ${ticker}!`);
                
                // Refresh prediction history table
                loadPredictionHistory();
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error('Prediction error:', xhr.responseJSON);
                
                if (xhr.status === 401) {
                    // Token expired or invalid
                    localStorage.removeItem('accessToken');
                    localStorage.removeItem('refreshToken');
                    showError('Session expired. Please log in again.');
                    setTimeout(function() {
                        window.location.href = '/login/';
                    }, 2000);
                } else if (xhr.status === 400) {
                    // Bad request - invalid ticker or other client error
                    const errorMsg = xhr.responseJSON?.error || 
                                    xhr.responseJSON?.detail || 
                                    'Invalid ticker symbol or request data';
                    showError(errorMsg);
                } else if (xhr.status >= 500) {
                    // Server error
                    showError('Server error occurred. Please try again later.');
                } else if (xhr.responseJSON) {
                    // Other API errors
                    const errorMsg = xhr.responseJSON.error || 
                                   xhr.responseJSON.detail || 
                                   'Prediction failed. Please try again.';
                    showError(errorMsg);
                } else {
                    // Network or unknown error
                    showError('Network error. Please check your connection and try again.');
                }
            },
            complete: function() {
                setLoading(false);
            }
        });
    });
    
    // Check authentication on page load
    checkAuthentication();
    
    // Load prediction history on page load
    loadPredictionHistory();
    
    // Clear messages when user starts typing
    $tickerInput.on('input', function() {
        hideMessages();
    });
    
    // Convert ticker to uppercase as user types
    $tickerInput.on('input', function() {
        const cursorPos = this.selectionStart;
        this.value = this.value.toUpperCase();
        this.setSelectionRange(cursorPos, cursorPos);
    });
});

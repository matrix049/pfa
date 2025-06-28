// Payment Processing JavaScript
class PaymentProcessor {
    constructor(bookingId, initialTimeRemaining) {
        this.bookingId = bookingId;
        this.timeRemaining = Math.max(0, initialTimeRemaining);
        this.countdownInterval = null;
        this.statusCheckInterval = null;
        
        this.init();
    }
    
    init() {
        if (this.timeRemaining <= 0) {
            this.handleExpiration();
            return;
        }
        
        this.updateTimerDisplay();
        this.startCountdown();
        this.startStatusCheck();
    }
    
    updateTimerDisplay() {
        const minutes = Math.floor(this.timeRemaining / 60);
        const seconds = this.timeRemaining % 60;
        
        const minutesElement = document.getElementById('minutes');
        const secondsElement = document.getElementById('seconds');
        
        if (minutesElement && secondsElement) {
            minutesElement.textContent = minutes.toString().padStart(2, '0');
            secondsElement.textContent = seconds.toString().padStart(2, '0');
        }
        
        // Update progress bar
        const progressPercent = (this.timeRemaining / (30 * 60)) * 100;
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            progressBar.style.width = `${progressPercent}%`;
            
            // Change color based on time remaining
            if (this.timeRemaining <= 300) { // 5 minutes
                progressBar.className = 'progress-bar bg-danger';
                const countdownTimer = document.getElementById('countdownTimer');
                if (countdownTimer) countdownTimer.classList.add('urgent');
            } else if (this.timeRemaining <= 600) { // 10 minutes
                progressBar.className = 'progress-bar bg-warning';
            }
        }
    }
    
    startCountdown() {
        this.countdownInterval = setInterval(() => {
            this.timeRemaining--;
            
            if (this.timeRemaining <= 0) {
                clearInterval(this.countdownInterval);
                this.handleExpiration();
            } else {
                this.updateTimerDisplay();
            }
        }, 1000);
    }
    
    startStatusCheck() {
        this.statusCheckInterval = setInterval(() => {
            this.checkBookingStatus();
        }, 5000); // Check every 5 seconds
    }
    
    async checkBookingStatus() {
        try {
            const response = await fetch(`/api/booking/${this.bookingId}/status/`);
            const data = await response.json();
            
            if (data.success) {
                if (data.status === 'confirmed' && data.payment_status === 'paid') {
                    this.handleSuccess();
                } else if (data.status === 'cancelled') {
                    this.handleCancellation();
                } else if (data.is_expired) {
                    this.handleExpiration();
                }
            }
        } catch (error) {
            console.error('Error checking booking status:', error);
        }
    }
    
    handleSuccess() {
        this.cleanup();
        
        const statusIndicator = document.getElementById('statusIndicator');
        const countdownTimer = document.getElementById('countdownTimer');
        const cancelBtn = document.getElementById('cancelBtn');
        const paymentBtn = document.getElementById('paymentBtn');
        
        if (statusIndicator) {
            statusIndicator.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i><span class="text-success">Payment successful! Redirecting...</span>';
        }
        
        if (countdownTimer) countdownTimer.style.display = 'none';
        if (cancelBtn) cancelBtn.disabled = true;
        if (paymentBtn) paymentBtn.disabled = true;
        
        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
            window.location.href = '/dashboard/';
        }, 2000);
    }
    
    handleExpiration() {
        this.cleanup();
        
        const statusIndicator = document.getElementById('statusIndicator');
        const countdownTimer = document.getElementById('countdownTimer');
        const cancelBtn = document.getElementById('cancelBtn');
        const paymentBtn = document.getElementById('paymentBtn');
        
        if (statusIndicator) {
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle text-danger me-2"></i><span class="text-danger">Reservation expired</span>';
        }
        
        if (countdownTimer) {
            countdownTimer.innerHTML = '<div class="timer-display text-danger">00:00</div><p class="timer-label">Time expired</p>';
        }
        
        if (cancelBtn) cancelBtn.disabled = true;
        if (paymentBtn) paymentBtn.disabled = true;
        
        // Redirect to dashboard after 3 seconds
        setTimeout(() => {
            window.location.href = '/dashboard/';
        }, 3000);
    }
    
    handleCancellation() {
        this.cleanup();
        
        const statusIndicator = document.getElementById('statusIndicator');
        const countdownTimer = document.getElementById('countdownTimer');
        const cancelBtn = document.getElementById('cancelBtn');
        const paymentBtn = document.getElementById('paymentBtn');
        
        if (statusIndicator) {
            statusIndicator.innerHTML = '<i class="fas fa-times-circle text-danger me-2"></i><span class="text-danger">Booking cancelled</span>';
        }
        
        if (countdownTimer) countdownTimer.style.display = 'none';
        if (cancelBtn) cancelBtn.disabled = true;
        if (paymentBtn) paymentBtn.disabled = true;
        
        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
            window.location.href = '/dashboard/';
        }, 2000);
    }
    
    cleanup() {
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        if (this.statusCheckInterval) clearInterval(this.statusCheckInterval);
    }
    
    async proceedToPayment() {
        try {
            const response = await fetch(`/api/booking/${this.bookingId}/stripe-session/`);
            const data = await response.json();
            
            if (data.url) {
                window.location.href = data.url;
            } else {
                alert('Error: Unable to proceed to payment. Please try again.');
            }
        } catch (error) {
            console.error('Error getting payment URL:', error);
            alert('Error: Unable to proceed to payment. Please try again.');
        }
    }
    
    cancelBooking() {
        if (confirm('Are you sure you want to cancel this booking?')) {
            const form = document.getElementById('cancelForm');
            if (form) form.submit();
        }
    }
}

// Global functions for onclick handlers
function proceedToPayment() {
    if (window.paymentProcessor) {
        window.paymentProcessor.proceedToPayment();
    }
}

function cancelBooking() {
    if (window.paymentProcessor) {
        window.paymentProcessor.cancelBooking();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // These values should be set by the template
    const bookingId = window.bookingId;
    const initialTimeRemaining = window.initialTimeRemaining;
    
    if (bookingId && initialTimeRemaining !== undefined) {
        window.paymentProcessor = new PaymentProcessor(bookingId, initialTimeRemaining);
    }
});

// Clean up when page unloads
window.addEventListener('beforeunload', function() {
    if (window.paymentProcessor) {
        window.paymentProcessor.cleanup();
    }
}); 
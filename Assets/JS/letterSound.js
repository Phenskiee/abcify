document.addEventListener('DOMContentLoaded', () => {
    const letters = document.querySelectorAll('.letter');
    
    letters.forEach(letter => {
        letter.addEventListener('click', function() {
            const audioFile = this.getAttribute('data-audio');
            const audio = new Audio(audioFile);
            
            audio.play();
        });
    });
});
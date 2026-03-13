const form = document.getElementById('loginForm');
if (form) {
    form.addEventListener('submit', function (e) {
        const user = document.getElementById('username').value.trim();
        const pass = document.getElementById('password').value.trim();

        if (!user || !pass) {
            e.preventDefault();
            alert('Completa usuario y contraseña');
            return;
        }

        // Guardar bandera para mostrar alerta en la página de inicio
        sessionStorage.setItem('showWelcome', '1');
        // dejar que el formulario se envíe al servidor (no preventDefault)
    });
}
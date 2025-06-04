// Garante que o DOM está completamente carregado antes de executar o script
document.addEventListener('DOMContentLoaded', () => {
    // Obtém o botão de alternância pelo seu ID
    const darkModeToggle = document.getElementById('darkModeToggle');
    // Obtém o elemento body do documento
    const body = document.body;
    // Define uma chave para guardar a preferência de tema no localStorage
    const themePreferenceKey = 'themePreference';

    // Função para aplicar o tema (claro ou escuro)
    function applyTheme(theme) {
        if (theme === 'dark') {
            // Adiciona a classe 'dark-mode' ao body para ativar os estilos escuros
            body.classList.add('dark-mode');
            // Atualiza o texto do botão para indicar a próxima ação (mudar para modo claro)
            if (darkModeToggle) { // Verifica se o botão existe na página
                darkModeToggle.textContent = 'Modo Claro';
            }
        } else {
            // Remove a classe 'dark-mode' do body para ativar os estilos claros
            body.classList.remove('dark-mode');
            // Atualiza o texto do botão para indicar a próxima ação (mudar para modo escuro)
            if (darkModeToggle) { // Verifica se o botão existe na página
                darkModeToggle.textContent = 'Modo Escuro';
            }
        }
    }

    // Verifica se já existe uma preferência de tema guardada no localStorage
    const currentTheme = localStorage.getItem(themePreferenceKey);

    if (currentTheme) {
        // Se existir uma preferência guardada, aplica-a
        applyTheme(currentTheme);
    } else {
        // Se não existir preferência, pode definir um padrão ou tentar detetar a preferência do sistema.
        // Por agora, vamos definir o modo claro como padrão se não houver preferência.
        // Para detetar a preferência do sistema (opcional e mais avançado):
        // if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        //    applyTheme('dark');
        // } else {
        //    applyTheme('light');
        // }
        applyTheme('light'); // Padrão para modo claro
    }

    // Adiciona um ouvinte de evento de clique ao botão de alternância
    // Só adiciona o ouvinte se o botão realmente existir na página atual
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            let newTheme;
            // Verifica se o corpo já tem a classe 'dark-mode'
            if (body.classList.contains('dark-mode')) {
                // Se sim, o novo tema será 'light'
                newTheme = 'light';
            } else {
                // Caso contrário, o novo tema será 'dark'
                newTheme = 'dark';
            }
            // Aplica o novo tema
            applyTheme(newTheme);
            // Guarda a nova preferência de tema no localStorage
            localStorage.setItem(themePreferenceKey, newTheme);
        });
    }
});

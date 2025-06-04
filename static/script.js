// Garante que o DOM está completamente carregado antes de executar o script
document.addEventListener('DOMContentLoaded', () => {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    const themePreferenceKey = 'themePreference';

    // Função centralizada para atualizar as cores de todos os gráficos conhecidos
    function updateAllChartColors(isDark) {
        if (typeof window.updateChartColorsForDashboard === 'function') {
            window.updateChartColorsForDashboard(isDark);
        }
        if (typeof window.updateChartColorsForDataPage === 'function') {
            window.updateChartColorsForDataPage(isDark);
        }
        // ADICIONADO: Chamada para atualizar as cores do gráfico de pizza no dashboard
        if (typeof window.updateChartColorsForPieDashboard === 'function') {
            window.updateChartColorsForPieDashboard(isDark);
        }
        // Adicione chamadas para outras funções de atualização de gráficos aqui, se necessário
    }

    // Função para aplicar o tema (claro ou escuro)
    function applyTheme(theme) {
        const isDark = theme === 'dark'; // Define se o tema é escuro

        if (isDark) {
            body.classList.add('dark-mode');
            if (darkModeToggle) { // Verifica se o botão existe na página
                darkModeToggle.textContent = 'Modo Claro';
            }
        } else {
            body.classList.remove('dark-mode');
            if (darkModeToggle) { // Verifica se o botão existe na página
                darkModeToggle.textContent = 'Modo Escuro';
            }
        }
        // Atualiza as cores dos gráficos após aplicar o tema ao body
        updateAllChartColors(isDark);
    }

    // Verifica a preferência de tema salva no localStorage ao carregar a página
    const savedTheme = localStorage.getItem(themePreferenceKey);

    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        // Opcional: Detectar preferência do sistema operacional
        // const prefersDarkScheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        // applyTheme(prefersDarkScheme ? 'dark' : 'light');
        applyTheme('light'); // Padrão para modo claro se nenhuma preferência salva ou do sistema
    }

    // Adiciona o ouvinte de evento de clique ao botão de alternância, se ele existir
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            // Alterna o tema atual
            const newTheme = body.classList.contains('dark-mode') ? 'light' : 'dark';
            applyTheme(newTheme);
            // Salva a nova preferência de tema no localStorage
            localStorage.setItem(themePreferenceKey, newTheme);
        });
    }
});
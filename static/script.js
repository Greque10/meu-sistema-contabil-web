// Garante que o DOM está completamente carregado antes de executar o script
document.addEventListener('DOMContentLoaded', () => {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    const themePreferenceKey = 'themePreference';

    // Função centralizada para atualizar as cores de todos os gráficos conhecidos na página atual
    function updateAllChartColors(isDark) {
        // Verifica se a função de atualização para o gráfico de barras do dashboard existe e a chama
        if (typeof window.updateChartColorsForDashboard === 'function') {
            window.updateChartColorsForDashboard(isDark);
        }
        // Verifica se a função de atualização para o gráfico por data existe e a chama
        if (typeof window.updateChartColorsForDataPage === 'function') {
            window.updateChartColorsForDataPage(isDark);
        }
        // Verifica se a função de atualização para o gráfico de pizza existe e a chama
        if (typeof window.updateChartColorsForPieDashboard === 'function') {
            window.updateChartColorsForPieDashboard(isDark);
        }
        // Adicione chamadas para outras funções de atualização de gráficos aqui, se necessário
    }

    // Função para aplicar o tema (claro ou escuro)
    function applyTheme(theme) {
        const isDark = theme === 'dark'; // Define se o tema é escuro

        // Adiciona ou remove a classe 'dark-mode' do body
        if (isDark) {
            body.classList.add('dark-mode');
        } else {
            body.classList.remove('dark-mode');
        }

        // Atualiza o texto do botão de alternância, se ele existir na página
        if (darkModeToggle) {
            darkModeToggle.textContent = isDark ? 'Modo Claro' : 'Modo Escuro';
        }
        
        // Atualiza as cores dos gráficos após aplicar o tema ao body
        updateAllChartColors(isDark);
    }

    // Verifica a preferência de tema salva no localStorage ao carregar a página
    const savedTheme = localStorage.getItem(themePreferenceKey);

    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        // Opcional: Detectar preferência do sistema operacional do utilizador
        // const prefersDarkScheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        // applyTheme(prefersDarkScheme ? 'dark' : 'light');
        
        // Padrão para modo claro se nenhuma preferência salva ou do sistema for detetada
        applyTheme('light'); 
    }

    // Adiciona o ouvinte de evento de clique ao botão de alternância, se ele existir
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            // Alterna o tema atual
            const newTheme = body.classList.contains('dark-mode') ? 'light' : 'dark';
            // Aplica o novo tema visualmente
            applyTheme(newTheme);
            // Salva a nova preferência de tema no localStorage para persistir a escolha
            localStorage.setItem(themePreferenceKey, newTheme);
        });
    }
});
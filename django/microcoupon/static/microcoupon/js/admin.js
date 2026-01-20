// サイドバーの開閉状態を管理
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    if (!sidebar || !mainContent) return;
    
    if (window.innerWidth <= 768) {
        // モバイル: サイドバーをオーバーレイ表示
        sidebar.classList.toggle('open');
        // オーバーレイ追加/削除
        if (sidebar.classList.contains('open')) {
            const overlay = document.createElement('div');
            overlay.className = 'sidebar-overlay';
            overlay.onclick = toggleSidebar;
            document.body.appendChild(overlay);
        } else {
            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) overlay.remove();
        }
    } else {
        // デスクトップ: サイドバーを隠してメインコンテンツを拡張
        sidebar.classList.toggle('closed');
        mainContent.classList.toggle('expanded');
    }
    
    // 状態を保存
    const isOpen = sidebar.classList.contains('open') || !sidebar.classList.contains('closed');
    localStorage.setItem('sidebarOpen', isOpen);
}

// ページ読み込み時にサイドバーの状態を復元
document.addEventListener('DOMContentLoaded', function() {
    const sidebarOpen = localStorage.getItem('sidebarOpen');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    if (!sidebar || !mainContent) return;
    
    // デスクトップで前回閉じていた場合
    if (sidebarOpen === 'false' && window.innerWidth > 768) {
        sidebar.classList.add('closed');
        mainContent.classList.add('expanded');
    }
    
    // ウィンドウリサイズ時の処理
    window.addEventListener('resize', function() {
        const overlay = document.querySelector('.sidebar-overlay');
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
            if (overlay) overlay.remove();
        } else {
            sidebar.classList.remove('closed');
            mainContent.classList.remove('expanded');
        }
    });
});

// メッセージの自動消去
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.animation = 'slideOut 0.3s ease';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
});

// スライドアウトアニメーション
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-10px);
        }
    }
`;
document.head.appendChild(style);

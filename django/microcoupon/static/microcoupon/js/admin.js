// サイドバーの開閉状態を管理
function toggleSidebar() {
    console.log('toggleSidebar called');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    if (!sidebar || !mainContent) {
        console.error('Sidebar or mainContent not found');
        return;
    }
    
    console.log('Window width:', window.innerWidth);
    
    if (window.innerWidth <= 768) {
        // モバイル: サイドバーをオーバーレイ表示
        console.log('Mobile mode - toggling sidebar');
        sidebar.classList.toggle('open');
        console.log('Sidebar classes:', sidebar.className);
        
        // オーバーレイ追加/削除
        let overlay = document.querySelector('.sidebar-overlay');
        
        if (sidebar.classList.contains('open')) {
            console.log('Opening sidebar - creating overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                overlay.onclick = toggleSidebar;
                document.body.appendChild(overlay);
                console.log('Overlay created and added to body');
            }
            // アニメーションのために少し遅延してクラスを追加
            setTimeout(() => {
                overlay.classList.add('show');
                console.log('Overlay show class added');
            }, 10);
        } else {
            console.log('Closing sidebar - removing overlay');
            if (overlay) {
                overlay.classList.remove('show');
                setTimeout(() => {
                    overlay.remove();
                    console.log('Overlay removed');
                }, 300);
            }
        }
    } else {
        // デスクトップ: サイドバーを隠してメインコンテンツを拡張
        console.log('Desktop mode - toggling sidebar');
        sidebar.classList.toggle('closed');
        mainContent.classList.toggle('expanded');
    }
    
    // 状態を保存
    const isOpen = sidebar.classList.contains('open') || !sidebar.classList.contains('closed');
    localStorage.setItem('sidebarOpen', isOpen);
    console.log('Sidebar state saved:', isOpen);
}

// ページ読み込み時にサイドバーの状態を復元
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded - initializing sidebar');
    const sidebarOpen = localStorage.getItem('sidebarOpen');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    if (!sidebar || !mainContent) {
        console.error('Sidebar or mainContent not found on load');
        return;
    }
    
    console.log('Sidebar element found:', sidebar);
    console.log('Window width on load:', window.innerWidth);
    
    // デスクトップで前回閉じていた場合
    if (sidebarOpen === 'false' && window.innerWidth > 768) {
        sidebar.classList.add('closed');
        mainContent.classList.add('expanded');
    }
    
    // ウィンドウリサイズ時の処理
    window.addEventListener('resize', function() {
        const overlay = document.querySelector('.sidebar-overlay');
        console.log('Window resized to:', window.innerWidth);
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
            if (overlay) {
                overlay.classList.remove('show');
                setTimeout(() => {
                    overlay.remove();
                }, 300);
            }
        } else {
            sidebar.classList.remove('closed');
            mainContent.classList.remove('expanded');
        }
    });
    
    console.log('Sidebar initialization complete');
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

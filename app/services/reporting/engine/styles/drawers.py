#!/usr/bin/env python3
"""Modal overlays, AI assistant chat drawer, and checkmarks."""

def get_drawer_styles(ctx: dict = None) -> str:
    """Return CSS chunk."""
    return _CSS

_CSS = r"""/* ── Section-Level AI Chat Styles ── */
        .ai-chat-fab {
            position: absolute;
            right: 1.25rem;
            bottom: 0.85rem;
            background: rgba(14, 165, 233, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 20px;
            padding: 0.35rem 0.85rem;
            font-size: 0.78rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            cursor: pointer;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2), 0 0 10px rgba(56, 189, 248, 0.15);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 20;
        }
        .light-mode .ai-chat-fab, html.light-mode .ai-chat-fab {
            background: rgba(2, 132, 199, 0.08);
            color: #0284c7;
            border-color: rgba(2, 132, 199, 0.3);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .ai-chat-fab:hover {
            transform: translateY(-2px);
            background: linear-gradient(135deg, #0284c7, #6366f1);
            color: #ffffff;
            border-color: transparent;
            box-shadow: 0 8px 22px rgba(2, 132, 199, 0.45);
        }
        .ai-chat-fab:active {
            transform: translateY(0);
        }

        .ai-chat-drawer {
            position: absolute;
            right: 1.25rem;
            bottom: 0.85rem;
            width: 600px;
            min-width: 380px;
            max-width: min(96vw, 1250px);
            height: 680px;
            min-height: 420px;
            max-height: calc(100vh - 45px);
            background: linear-gradient(165deg, rgba(30, 41, 59, 0.96) 0%, rgba(15, 23, 42, 0.98) 100%);
            backdrop-filter: blur(24px) saturate(190%);
            -webkit-backdrop-filter: blur(24px) saturate(190%);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 16px;
            box-shadow: 0 24px 60px -10px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.08);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            z-index: 1000;
            transform: scale(0.95) translateY(14px);
            opacity: 0;
            pointer-events: none;
            transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
        }
        .light-mode .ai-chat-drawer, html.light-mode .ai-chat-drawer {
            background: linear-gradient(165deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
            border: 1px solid rgba(2, 132, 199, 0.2);
            box-shadow: 0 24px 60px -10px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
        }
        .ai-chat-drawer.open {
            transform: scale(1) translateY(0);
            opacity: 1;
            pointer-events: auto;
        }

        /* ── Resizing Handles & Interactive Elements ── */
        .ai-chat-resize-handle-nw {
            position: absolute;
            top: 0;
            left: 0;
            width: 22px;
            height: 22px;
            cursor: nwse-resize;
            z-index: 120;
            user-select: none;
            touch-action: none;
        }
        .ai-chat-resize-handle-nw::after {
            content: '';
            position: absolute;
            top: 4px;
            left: 4px;
            width: 10px;
            height: 10px;
            border-top: 2px solid rgba(56, 189, 248, 0.7);
            border-left: 2px solid rgba(56, 189, 248, 0.7);
            border-top-left-radius: 4px;
            transition: all 0.2s ease;
        }
        .ai-chat-resize-handle-nw:hover::after {
            border-color: #38bdf8;
            box-shadow: -1px -1px 6px rgba(56, 189, 248, 0.6);
            transform: scale(1.15);
        }

        .ai-chat-resize-edge-n {
            position: absolute;
            top: 0;
            left: 22px;
            right: 22px;
            height: 8px;
            cursor: ns-resize;
            z-index: 115;
            touch-action: none;
        }
        .ai-chat-resize-edge-w {
            position: absolute;
            top: 22px;
            left: 0;
            bottom: 22px;
            width: 8px;
            cursor: ew-resize;
            z-index: 115;
            touch-action: none;
        }
        .ai-chat-resize-edge-s {
            position: absolute;
            bottom: 0;
            left: 22px;
            right: 22px;
            height: 8px;
            cursor: ns-resize;
            z-index: 115;
            touch-action: none;
        }
        .ai-chat-resize-edge-e {
            position: absolute;
            top: 22px;
            right: 0;
            bottom: 22px;
            width: 8px;
            cursor: ew-resize;
            z-index: 115;
            touch-action: none;
        }

        .ai-chat-resize-handle-se {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 22px;
            height: 22px;
            cursor: nwse-resize;
            z-index: 120;
            user-select: none;
            touch-action: none;
        }
        .ai-chat-resize-handle-se::after {
            content: '';
            position: absolute;
            bottom: 4px;
            right: 4px;
            width: 10px;
            height: 10px;
            border-bottom: 2px solid rgba(56, 189, 248, 0.7);
            border-right: 2px solid rgba(56, 189, 248, 0.7);
            border-bottom-right-radius: 4px;
            transition: all 0.2s ease;
        }
        .ai-chat-resize-handle-se:hover::after {
            border-color: #38bdf8;
            box-shadow: 1px 1px 6px rgba(56, 189, 248, 0.6);
            transform: scale(1.15);
        }

        /* ── Fullscreen / Expanded Mode ── */
        .ai-chat-drawer.expanded {
            position: fixed !important;
            right: 1.5rem !important;
            bottom: 1.5rem !important;
            width: min(1120px, calc(100vw - 3rem)) !important;
            height: min(880px, calc(100vh - 3rem)) !important;
            max-width: calc(100vw - 3rem) !important;
            max-height: calc(100vh - 3rem) !important;
            z-index: 9999 !important;
            box-shadow: 0 32px 80px -12px rgba(0, 0, 0, 0.85), 0 0 0 1px rgba(56, 189, 248, 0.4) !important;
        }

        .ai-chat-drawer.is-resizing {
            transition: none !important;
            user-select: none !important;
        }

        @media (max-width: 640px) {
            .ai-chat-drawer {
                width: calc(100vw - 1.5rem) !important;
                right: 0.75rem !important;
                bottom: 0.75rem !important;
                height: calc(100vh - 1.5rem) !important;
                max-width: 100vw !important;
                max-height: 100vh !important;
            }
        }

        .ai-chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.85rem 1.15rem;
            background: rgba(30, 41, 59, 0.75);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-bottom: 1px solid var(--border);
        }
        .light-mode .ai-chat-header, html.light-mode .ai-chat-header {
            background: rgba(241, 245, 249, 0.85);
        }
        .ai-chat-title-wrap {
            display: flex;
            align-items: center;
            gap: 0.55rem;
        }
        .ai-chat-title-icon {
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: var(--accent-bg);
            border: 1px solid rgba(56, 189, 248, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
        }
        .ai-chat-title-text {
            font-weight: 700;
            color: var(--text);
            font-size: 0.88rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }
        .ai-chat-status-dot {
            width: 6px;
            height: 6px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10b981;
            display: inline-block;
        }
        .ai-chat-hdr-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--muted);
            border-radius: 8px;
            width: 28px;
            height: 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s ease;
        }
        .ai-chat-hdr-btn:hover {
            background: var(--surface2);
            color: var(--text);
            border-color: var(--accent);
            transform: scale(1.05);
        }

        .ai-chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            background: transparent;
        }
        .ai-chat-messages::-webkit-scrollbar {
            width: 5px;
        }
        .ai-chat-messages::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.25);
            border-radius: 3px;
        }

        .ai-chat-welcome {
            text-align: center;
            padding: 1.5rem 0.75rem;
            margin: auto 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .ai-welcome-avatar {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(2, 132, 199, 0.2), rgba(99, 102, 241, 0.2));
            border: 1px solid rgba(56, 189, 248, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            margin-bottom: 0.65rem;
            box-shadow: 0 6px 18px rgba(2, 132, 199, 0.2);
        }
        .ai-welcome-title {
            font-weight: 800;
            font-size: 0.98rem;
            color: var(--text);
            margin-bottom: 0.25rem;
        }
        .ai-welcome-sub {
            font-size: 0.78rem;
            color: var(--muted);
            line-height: 1.45;
            max-width: 440px;
            margin-bottom: 1rem;
        }
        .ai-quick-prompts {
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
            width: 100%;
            max-width: 480px;
        }
        .ai-quick-chip {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.48rem 0.78rem;
            font-size: 0.78rem;
            color: var(--text);
            text-align: left;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .ai-quick-chip:hover {
            border-color: var(--accent);
            background: var(--accent-bg);
            color: var(--accent);
            transform: translateX(3px);
        }

        .ai-chat-bubble-user {
            align-self: flex-end;
            max-width: 84%;
            background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
            color: #ffffff;
            padding: 0.65rem 0.95rem;
            border-radius: 14px 14px 3px 14px;
            font-size: 0.82rem;
            line-height: 1.5;
            word-break: break-word;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.25);
        }

        .ai-chat-bubble-ai {
            align-self: flex-start;
            max-width: 92%;
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.75rem 1rem;
            border-radius: 14px 14px 14px 3px;
            font-size: 0.82rem;
            line-height: 1.6;
            word-break: break-word;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }
        .ai-chat-bubble-ai strong {
            color: var(--accent);
            font-weight: 700;
        }
        .ai-chat-bubble-ai code {
            background: var(--surface2);
            border: 1px solid var(--border);
            padding: 0.12rem 0.4rem;
            border-radius: 4px;
            font-size: 0.78rem;
            font-family: 'JetBrains Mono', monospace;
            color: #f43f5e;
        }

        .ai-chat-typing {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 0.6rem 0.85rem;
        }
        .typing-dot {
            width: 6px;
            height: 6px;
            background: var(--accent);
            border-radius: 50%;
            animation: typingPulse 1.2s infinite ease-in-out;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typingPulse {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
            40% { transform: scale(1.1); opacity: 1; }
        }

        .ai-chat-input-box {
            padding: 0.75rem 1rem;
            background: rgba(30, 41, 59, 0.75);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-top: 1px solid var(--border);
            display: flex;
            gap: 0.6rem;
            align-items: center;
        }
        .light-mode .ai-chat-input-box, html.light-mode .ai-chat-input-box {
            background: rgba(241, 245, 249, 0.85);
        }
        .ai-chat-input {
            flex: 1;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.55rem 0.95rem;
            color: var(--text);
            font-size: 0.82rem;
            outline: none;
            font-family: inherit;
            transition: all 0.2s ease;
        }
        .ai-chat-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-bg);
            background: var(--surface1);
        }
        .ai-chat-send-btn {
            background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
            color: #ffffff;
            font-weight: 700;
            border: none;
            border-radius: 20px;
            padding: 0.5rem 0.95rem;
            cursor: pointer;
            font-size: 0.78rem;
            flex-shrink: 0;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            box-shadow: 0 2px 8px rgba(2, 132, 199, 0.35);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .ai-chat-send-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.55);
            filter: brightness(1.1);
        }
        .ai-chat-send-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
            transform: none;
        }

        /* Agentic Action / Patch Proposal Card & Interactive Preview in Chat */
        .patch-action-box {
            margin-top: 0.75rem;
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-left: 4px solid #10b981;
            border-radius: 10px;
            padding: 0.85rem 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
        }
        .patch-action-title {
            font-size: 0.78rem;
            font-weight: 800;
            color: var(--green);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .patch-preview-wrap {
            background: var(--surface);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            font-size: 0.8rem;
            max-height: 220px;
            overflow-y: auto;
        }
        .patch-preview-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--muted);
            margin-bottom: 0.4rem;
            padding-bottom: 0.25rem;
            border-bottom: 1px solid var(--border);
        }
        .patch-edit-badge {
            color: var(--accent);
            font-weight: 600;
            font-size: 0.7rem;
            background: var(--accent-bg);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
        }
        .patch-preview-bullets {
            margin: 0;
            padding-left: 1.15rem;
            color: var(--text);
            line-height: 1.55;
            outline: none;
        }
        .patch-preview-bullets:focus, .patch-preview-obs-text:focus {
            background: rgba(56, 189, 248, 0.05);
            border-radius: 4px;
        }
        .patch-preview-obs-item {
            margin-bottom: 0.45rem;
            padding-bottom: 0.35rem;
            border-bottom: 1px dashed var(--border);
        }
        .patch-preview-obs-cat {
            font-weight: 700;
            color: var(--accent);
            font-size: 0.75rem;
            margin-bottom: 0.15rem;
        }
        .patch-preview-obs-text {
            color: var(--text);
            line-height: 1.45;
            outline: none;
        }
        .patch-preview-rec-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem 0.7rem;
            margin-bottom: 0.4rem;
        }
        .patch-priority-chip {
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--muted);
        }
        .patch-apply-btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: #ffffff;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 0.95rem;
            font-size: 0.8rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
            box-shadow: 0 3px 12px rgba(16, 185, 129, 0.35);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            width: 100%;
        }
        .patch-apply-btn:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.5);
        }
        .patch-apply-btn.applied {
            background: var(--surface2);
            color: var(--green);
            border: 1px solid rgba(16, 185, 129, 0.4);
            box-shadow: none;
            cursor: default;
            transform: none;
        }


        /* Section Live Highlight Animation */
        @keyframes sectionGlow {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
            25% { box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.5), 0 0 20px rgba(16, 185, 129, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .section-just-updated {
            animation: sectionGlow 2s ease-out;
            border-color: rgba(16, 185, 129, 0.6) !important;
        }

        /* ── """

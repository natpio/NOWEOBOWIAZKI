                    </div>
                    <div>
                        <div style="color: #E2DCD3; font-family: 'Inter', sans-serif; font-weight: 700; font-size: 14px; letter-spacing: 0.5px;">Piotr Dukiel</div>
                        <div style="color: #C5A880; font-family: 'Inter', sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;">Logistics Manager</div>
                        <div style="color: #8C8477; font-size: 10px; font-style: italic; margin-top: 4px;">Let's hit it out of the park.<br><span style="color:#BA4949; font-weight:bold;">Szef!</span></div>
                        <div style="color: #BA4949; font-size: 14px; margin-top: 2px;">★ ★ ★</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # REFRESH THE LINEUP GRAPHIC
        st.markdown('''
            <div class="refresh-graphic">
                <div class="rg-title">REFRESH</div>
                <div class="rg-subtitle">THE LINEUP</div>
                <div class="rg-icon">🏏⚾🏏</div>
            </div>
        ''', unsafe_allow_html=True)

        # STYLIZOWANE PRZYCISKI
        st.markdown('<div class="sidebar-buttons">', unsafe_allow_html=True)
        if st.button("🔄 ODŚWIEŻ DANE / REFRESH", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if st.button("🚪 WYLOGUJ / ログアウト", use_container_width=True):
            st.session_state["zalogowany"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ROUTING MODUŁÓW ---
    if wybrany_modul == "COMMAND CENTER": mod_command_center.render(sh)
    elif wybrany_modul == "HARMONOGRAM (GANTT)": mod_harmonogram.render(sh)
    elif wybrany_modul == "GENERATOR ZLECEŃ PRO": mod_generator_pdf.render(sh) 
    elif wybrany_modul == "EVENTY / TARGI": mod_eventy.render(sh)
    elif wybrany_modul == "ZLECENIA POBOCZNE": mod_zlecenia_poboczne.render(sh)
    elif wybrany_modul == "SUBRENTY": mod_subrenty.render(sh)
    elif wybrany_modul == "YESTECH EXPORT": mod_yestech.render(sh)
    elif wybrany_modul == "BAZY DANYCH / SŁOWNIKI": mod_bazy_danych.render(sh)
    elif wybrany_modul == "FINANSE I RAPORTY": mod_finanse.render(sh)

if __name__ == "__main__":
    main()

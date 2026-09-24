// =============================================================================
// HYDROGUARD — CLIENTE DINÁMICO CONECTADO A POSTGRESQL EN VIVO
// =============================================================================

const PLAN_TIERS = ['BASE', 'ESTANDAR', 'PREMIUM'];
let currentPlanIndex = 0;
let sliderDebounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log("HydroGuard cargado. Conectando a PostgreSQL...");
    fetchLiveState();
});

// Obtener Plan Actual
function getCurrentTier() {
    return PLAN_TIERS[currentPlanIndex];
}

// -----------------------------------------------------------------------------
// 1. GESTIÓN DE PLANES (BASE -> ESTÁNDAR -> PREMIUM)
// -----------------------------------------------------------------------------
function cyclePlan() {
    currentPlanIndex = (currentPlanIndex + 1) % PLAN_TIERS.length;
    applyPlan(PLAN_TIERS[currentPlanIndex]);
}

function setPlan(planName) {
    const idx = PLAN_TIERS.indexOf(planName);
    if (idx !== -1) {
        currentPlanIndex = idx;
        applyPlan(PLAN_TIERS[currentPlanIndex]);
    }
}

function applyPlan(plan) {
    const pill = document.getElementById('userPlanPill');
    const pillTxt = document.getElementById('txtUserPlan');
    const pillIcon = document.getElementById('planPillIcon');
    const sidebarTag = document.getElementById('sidebarPlanTag');
    const drawerTag = document.getElementById('drawerPlanTag');

    const secGen = document.getElementById('secGenerator');
    const secSolar = document.getElementById('secSolar');
    const sidebarLinkGen = document.getElementById('sidebarLinkGen');
    const sidebarLinkSolar = document.getElementById('sidebarLinkSolar');

    const calibRowGen = document.getElementById('calibRowGen');
    const calibRowSolar = document.getElementById('calibRowSolar');

    if (plan === 'BASE') {
        if (pill) pill.className = 'user-plan-pill plan-base';
        if (pillTxt) pillTxt.textContent = 'PLAN BASE';
        if (pillIcon) pillIcon.className = 'fa-solid fa-leaf plan-pill-icon';
        if (sidebarTag) {
            sidebarTag.textContent = 'Plan Base Activo';
            sidebarTag.className = 'user-plan-tag plan-base';
        }
        if (drawerTag) {
            drawerTag.textContent = 'Plan Base Activo';
            drawerTag.className = 'drawer-plan-tag plan-base';
        }

        // Ocultar módulos no contratados
        if (secGen) secGen.style.display = 'none';
        if (secSolar) secSolar.style.display = 'none';
        if (sidebarLinkGen) sidebarLinkGen.style.display = 'none';
        if (sidebarLinkSolar) sidebarLinkSolar.style.display = 'none';

        if (calibRowGen) calibRowGen.style.display = 'none';
        if (calibRowSolar) calibRowSolar.style.display = 'none';

        showToast("🌱 <strong>Plan Base Activo:</strong> Monitoreo de Tanques y Microclima.");

    } else if (plan === 'ESTANDAR') {
        if (pill) pill.className = 'user-plan-pill plan-estandar';
        if (pillTxt) pillTxt.textContent = 'PLAN ESTÁNDAR';
        if (pillIcon) pillIcon.className = 'fa-solid fa-bolt plan-pill-icon';
        if (sidebarTag) {
            sidebarTag.textContent = 'Plan Estándar Activo';
            sidebarTag.className = 'user-plan-tag plan-estandar';
        }
        if (drawerTag) {
            drawerTag.textContent = 'Plan Estándar Activo';
            drawerTag.className = 'drawer-plan-tag plan-estandar';
        }

        // Mostrar Generador y ocultar Solar
        if (secGen) secGen.style.display = 'flex';
        if (secSolar) secSolar.style.display = 'none';
        if (sidebarLinkGen) sidebarLinkGen.style.display = 'flex';
        if (sidebarLinkSolar) sidebarLinkSolar.style.display = 'none';

        if (calibRowGen) calibRowGen.style.display = 'flex';
        if (calibRowSolar) calibRowSolar.style.display = 'none';

        showToast("⚡ <strong>Plan Estándar Activo:</strong> Generador & Combustible desbloqueado.");

    } else if (plan === 'PREMIUM') {
        if (pill) pill.className = 'user-plan-pill plan-premium';
        if (pillTxt) pillTxt.textContent = 'PLAN PREMIUM';
        if (pillIcon) pillIcon.className = 'fa-solid fa-crown plan-pill-icon';
        if (sidebarTag) {
            sidebarTag.textContent = 'Plan Premium Activo';
            sidebarTag.className = 'user-plan-tag plan-premium';
        }
        if (drawerTag) {
            drawerTag.textContent = 'Plan Premium Activo';
            drawerTag.className = 'drawer-plan-tag plan-premium';
        }

        // Mostrar Generador y Solar
        if (secGen) secGen.style.display = 'flex';
        if (secSolar) secSolar.style.display = 'flex';
        if (sidebarLinkGen) sidebarLinkGen.style.display = 'flex';
        if (sidebarLinkSolar) sidebarLinkSolar.style.display = 'flex';

        if (calibRowGen) calibRowGen.style.display = 'flex';
        if (calibRowSolar) calibRowSolar.style.display = 'flex';

        showToast("👑 <strong>Plan Premium Activo:</strong> Sistema Solar & Baterías desbloqueado.");
    }

    // Sincronizar lecturas de la base de datos para este plan
    fetchLiveState();
}

// -----------------------------------------------------------------------------
// 2. SINCRONIZACIÓN CON POSTGRESQL EN VIVO (FETCH STATE & ALERTS)
// -----------------------------------------------------------------------------
async function fetchLiveState() {
    const tier = getCurrentTier();
    try {
        const response = await fetch(`/api/v1/simulation/state?tier=${tier}`);
        if (!response.ok) throw new Error("Error al consultar estado de la BD");
        
        const data = await response.json();
        updateUIFromData(data);
    } catch (err) {
        console.warn("Modo local / error al conectar a la API:", err);
    }
}

function updateUIFromData(data) {
    if (!data || !data.sensors) return;

    const s = data.sensors;

    // 1. Tanque Principal #1 (pH)
    if (s.TANK_1_PH) {
        const phVal = s.TANK_1_PH.current_value;
        const valPH1 = document.getElementById('valPH1');
        const rangePH1 = document.getElementById('rangePH1');
        const iconPH1 = document.getElementById('iconPH1');
        const boxPH1 = document.getElementById('metricBoxPH1');

        if (valPH1) {
            valPH1.textContent = phVal.toFixed(1);
            valPH1.className = s.TANK_1_PH.status === 'CRITICAL' ? 'text-rose' : (s.TANK_1_PH.status === 'WARNING' ? 'text-amber' : '');
        }
        if (rangePH1) {
            if (s.TANK_1_PH.status === 'CRITICAL') {
                rangePH1.innerHTML = `Rango: <strong>Fuera (${s.TANK_1_PH.min_safe} - ${s.TANK_1_PH.max_safe})</strong>`;
                rangePH1.className = 'tank-metric-range text-rose';
            } else {
                rangePH1.innerHTML = `Rango Óptimo: <strong>${s.TANK_1_PH.min_safe} - ${s.TANK_1_PH.max_safe}</strong>`;
                rangePH1.className = 'tank-metric-range';
            }
        }
        if (iconPH1) {
            iconPH1.className = s.TANK_1_PH.status === 'CRITICAL' ? 'fa-solid fa-vial text-rose' : 'fa-solid fa-vial text-cyan';
        }
        if (boxPH1) {
            if (s.TANK_1_PH.status === 'CRITICAL') boxPH1.classList.add('critical-metric');
            else boxPH1.classList.remove('critical-metric');
        }

        // Sincronizar slider de calibración
        const sliderPH = document.getElementById('sliderPH');
        const lblSliderPH = document.getElementById('lblSliderPH');
        if (sliderPH && document.activeElement !== sliderPH) sliderPH.value = phVal;
        if (lblSliderPH) lblSliderPH.textContent = `${phVal.toFixed(1)} pH`;
    }

    // 2. Tanque Principal #1 (Nivel de Agua)
    if (s.TANK_1_WATER_LEVEL) {
        const lvlVal = s.TANK_1_WATER_LEVEL.current_value;
        const valLvl1 = document.getElementById('valLevel1');
        const lblLiters1 = document.getElementById('lblLiters1');
        const rangeLvl1 = document.getElementById('rangeLevel1');
        const iconLvl1 = document.getElementById('iconLevel1');
        const boxLvl1 = document.getElementById('metricBoxLevel1');
        const fillLvl1 = document.getElementById('progressFillLevel1');

        if (valLvl1) {
            valLvl1.textContent = Math.round(lvlVal);
            valLvl1.className = s.TANK_1_WATER_LEVEL.status === 'CRITICAL' ? 'text-rose' : (s.TANK_1_WATER_LEVEL.status === 'WARNING' ? 'text-amber' : '');
        }
        if (lblLiters1) lblLiters1.textContent = `% (${Math.round(lvlVal * 10)} L)`;
        if (rangeLvl1) {
            if (s.TANK_1_WATER_LEVEL.status === 'CRITICAL') {
                rangeLvl1.innerHTML = `Rango: <strong>Bajo (> ${s.TANK_1_WATER_LEVEL.min_safe} %)</strong>`;
                rangeLvl1.className = 'tank-metric-range text-rose';
            } else {
                rangeLvl1.innerHTML = `Rango Óptimo: <strong>> ${s.TANK_1_WATER_LEVEL.min_safe} %</strong>`;
                rangeLvl1.className = 'tank-metric-range';
            }
        }
        if (iconLvl1) {
            iconLvl1.className = s.TANK_1_WATER_LEVEL.status === 'CRITICAL' ? 'fa-solid fa-water-ladder text-rose' : 'fa-solid fa-water-ladder text-emerald';
        }
        if (boxLvl1) {
            if (s.TANK_1_WATER_LEVEL.status === 'CRITICAL') boxLvl1.classList.add('critical-metric');
            else boxLvl1.classList.remove('critical-metric');
        }
        if (fillLvl1) {
            fillLvl1.style.width = `${lvlVal}%`;
            fillLvl1.className = s.TANK_1_WATER_LEVEL.status === 'CRITICAL' ? 'progress-fill red' : 'progress-fill green';
        }

        // Sincronizar slider
        const sliderLevel = document.getElementById('sliderLevel');
        const lblSliderLevel = document.getElementById('lblSliderLevel');
        if (sliderLevel && document.activeElement !== sliderLevel) sliderLevel.value = lvlVal;
        if (lblSliderLevel) lblSliderLevel.textContent = `${Math.round(lvlVal)} %`;
    }

    // Cabecera de la Tarjeta del Tanque #1
    const tankCard1 = document.getElementById('tankCard1');
    const tankAvatar1 = document.getElementById('tankAvatar1');
    const tankPill1 = document.getElementById('tankStatusPill1');
    const isTank1Crit = (s.TANK_1_PH && s.TANK_1_PH.status === 'CRITICAL') || (s.TANK_1_WATER_LEVEL && s.TANK_1_WATER_LEVEL.status === 'CRITICAL');

    if (tankCard1) {
        if (isTank1Crit) tankCard1.classList.add('critical-card');
        else tankCard1.classList.remove('critical-card');
    }
    if (tankAvatar1) {
        tankAvatar1.className = isTank1Crit ? 'tank-avatar-circle critical-avatar' : 'tank-avatar-circle';
    }
    if (tankPill1) {
        tankPill1.className = isTank1Crit ? 'status-indicator-pill crit' : 'status-indicator-pill opt';
        tankPill1.textContent = isTank1Crit ? 'Atención' : 'Óptimo';
    }

    // 3. Renderizar Alertas Activas desde PostgreSQL
    renderAlertsFeed(data.active_alerts || []);
}

function renderAlertsFeed(alerts) {
    const alertsFeed = document.getElementById('alertsFeed');
    const activeCountBadge = document.getElementById('activeAlertsCount');
    const notifBadge = document.getElementById('notifBadge');
    const sidebarAlertCount = document.getElementById('sidebarAlertCount');

    const totalCount = alerts.length;
    if (activeCountBadge) activeCountBadge.textContent = `${totalCount} activa${totalCount === 1 ? '' : 's'}`;
    if (notifBadge) notifBadge.textContent = totalCount;
    if (sidebarAlertCount) sidebarAlertCount.textContent = totalCount;

    if (!alertsFeed) return;

    if (totalCount === 0) {
        alertsFeed.innerHTML = `
            <div class="alert-card resolved-card" style="grid-column: 1 / -1;">
                <div class="alert-card-top">
                    <div class="alert-type-group">
                        <div class="alert-icon-circle resolved">
                            <i class="fa-solid fa-circle-check"></i>
                        </div>
                        <div class="alert-meta">
                            <span class="alert-category">Monitoreo en Tiempo Real</span>
                            <h4 class="alert-item-title">Todos los sistemas óptimos</h4>
                        </div>
                    </div>
                    <span class="badge-status-pill badge-resolved">NORMAL</span>
                </div>
                <p class="alert-description" style="color: #15803d; font-weight: 600;">
                    No hay alertas activas en la base de datos. Los tanques y el microclima están en rangos seguros.
                </p>
            </div>
        `;
        return;
    }

    let html = '';
    alerts.forEach(a => {
        const isCritical = a.severity === 'CRITICAL';
        const cardClass = isCritical ? 'alert-card critical' : 'alert-card warning';
        const iconCircleClass = isCritical ? 'alert-icon-circle critical' : 'alert-icon-circle warning';
        const badgeClass = isCritical ? 'badge-status-pill badge-critical' : 'badge-status-pill badge-warning';
        const badgeText = isCritical ? 'CRÍTICO' : 'ATENCIÓN';
        const icon = isCritical ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-temperature-half';

        html += `
            <div class="${cardClass}" id="alert_card_${a.id}">
                <div class="alert-card-top">
                    <div class="alert-type-group">
                        <div class="${iconCircleClass}">
                            <i class="${icon}"></i>
                        </div>
                        <div class="alert-meta">
                            <span class="alert-category">${a.sensor_code ? a.sensor_code.replace(/_/g, ' ') : 'Invernadero'}</span>
                            <h4 class="alert-item-title">${a.title}</h4>
                        </div>
                    </div>
                    <span class="${badgeClass}">${badgeText}</span>
                </div>
                <p class="alert-description">${a.message}</p>
                <button class="btn-action-suggested ${isCritical ? 'critical' : 'warning'}" onclick="resolveAction('tanque')">
                    <span>Acción sugerida: Normalizar y dosificar parámetros</span>
                    <i class="fa-solid fa-chevron-right"></i>
                </button>
            </div>
        `;
    });

    alertsFeed.innerHTML = html;
}

// -----------------------------------------------------------------------------
// 3. MODIFICACIÓN DE PARÁMETROS EN VIVO Y CALIBRACIÓN (API POSTGRESQL)
// -----------------------------------------------------------------------------
function onSliderChange(sensorCode, value, labelId, unit) {
    const lbl = document.getElementById(labelId);
    if (lbl) lbl.textContent = `${value}${unit}`;

    clearTimeout(sliderDebounceTimer);
    sliderDebounceTimer = setTimeout(async () => {
        try {
            const tier = getCurrentTier();
            const res = await fetch('/api/v1/simulation/update-reading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sensor_code: sensorCode,
                    value: parseFloat(value),
                    tier: tier
                })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.alert_triggered) {
                    showToast(`🚨 <strong>${data.alert_triggered.title}:</strong> ${data.alert_triggered.message}`);
                }
                fetchLiveState();
            }
        } catch (err) {
            console.error("Error al actualizar telemetría en BD:", err);
        }
    }, 250);
}

// Presets Rápidos
async function applyPreset(presetName) {
    const tier = getCurrentTier();
    try {
        const res = await fetch('/api/v1/simulation/preset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                preset: presetName,
                tier: tier
            })
        });

        if (res.ok) {
            showToast(`⚡ <strong>Escenario aplicado:</strong> ${presetName.toUpperCase()} en PostgreSQL.`);
            fetchLiveState();
            closeCalibrationModal();
        }
    } catch (err) {
        console.error("Error al aplicar preset:", err);
    }
}

// Resolver Alertas y Normalizar Parámetros en PostgreSQL
async function resolveAction(type) {
    const tier = getCurrentTier();
    const btn = document.getElementById('btnActionTank1');
    if (btn) {
        btn.innerHTML = `<span><i class="fa-solid fa-spinner fa-spin"></i> Dosificando y sincronizando con BD...</span>`;
        btn.disabled = true;
    }

    try {
        const res = await fetch('/api/v1/simulation/resolve-alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sensor_code: 'TANK_1_PH',
                tier: tier
            })
        });

        if (res.ok) {
            showToast("✅ <strong>Acción completada:</strong> Parámetros normalizados y alerta resuelta en PostgreSQL.");
            setTimeout(() => {
                fetchLiveState();
            }, 400);
        }
    } catch (err) {
        console.error("Error al resolver alerta en BD:", err);
    }
}

// -----------------------------------------------------------------------------
// 4. CONTROL DE MODALES Y MENÚS
// -----------------------------------------------------------------------------
function openCalibrationModal() {
    const modal = document.getElementById('calibrationModalOverlay');
    if (modal) modal.classList.add('open');
    const drawer = document.getElementById('sideDrawer');
    if (drawer && drawer.classList.contains('open')) toggleMenu();
}

function closeCalibrationModal(event) {
    if (event && event.target && event.target.id !== 'calibrationModalOverlay' && !event.target.classList.contains('btn-close-modal') && !event.target.classList.contains('btn-calib-done')) {
        return;
    }
    const modal = document.getElementById('calibrationModalOverlay');
    if (modal) modal.classList.remove('open');
}

function toggleExtraTanks() {
    const extraSection = document.getElementById('extraTanksSection');
    const btn = document.getElementById('btnToggleMoreTanks');
    const txt = document.getElementById('txtSeeMoreTanks');

    if (!extraSection || !btn || !txt) return;

    extraSection.classList.toggle('open');
    btn.classList.toggle('open');

    if (extraSection.classList.contains('open')) {
        txt.textContent = 'Ver menos tanques';
    } else {
        txt.textContent = 'Ver más tanques (+3 adicionales)';
    }
}

function toggleMenu() {
    const drawer = document.getElementById('sideDrawer');
    const overlay = document.getElementById('drawerOverlay');
    if (drawer && overlay) {
        drawer.classList.toggle('open');
        overlay.classList.toggle('open');
    }
}

function showToast(message) {
    let toast = document.getElementById('toastNotification');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toastNotification';
        toast.className = 'toast-notification';
        document.body.appendChild(toast);
    }
    toast.innerHTML = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

function scrollToAlerts() {
    const el = document.getElementById('secAlerts');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function addNewTankPrompt() {
    const name = prompt("Nombre del nuevo tanque a monitorear (ej. Tanque #5 - Riego Forraje):");
    if (name) {
        showToast(`✅ Tanque "${name}" agregado con éxito.`);
        const drawer = document.getElementById('sideDrawer');
        if (drawer && drawer.classList.contains('open')) toggleMenu();
    }
}

function openPlanModal() {
    const choice = prompt("🌿 SELECCIÓN DE PLAN HYDROGUARD:\n\n1 - Plan Base (Tanques + Microclima Invernadero)\n2 - Plan Estándar (Todo Base + Generador Diésel & Combustible)\n3 - Plan Premium (Todo Estándar + Sistema Solar & Baterías)\n\nEscribe 1, 2 o 3 para activar:");
    if (choice === '1') setPlan('BASE');
    else if (choice === '2') setPlan('ESTANDAR');
    else if (choice === '3') setPlan('PREMIUM');
    const drawer = document.getElementById('sideDrawer');
    if (drawer && drawer.classList.contains('open')) toggleMenu();
}

function changeGreenhouse() {
    const sel = document.getElementById('ghSelect').value;
    showToast(`🌱 Cambiando a Invernadero #${sel}...`);
    fetchLiveState();
}

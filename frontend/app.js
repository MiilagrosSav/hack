// =============================================================================
// HYDROGUARD — CLIENTE DINÁMICO CONECTADO A POSTGRESQL EN VIVO
// =============================================================================

const PLAN_TIERS = ['BASE', 'ESTANDAR', 'PREMIUM'];
let currentPlanIndex = 0;
let sliderDebounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log("HydroGuard Dashboard cargado. Conectando a PostgreSQL...");
    fetchLiveState();
});

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

        if (secGen) secGen.style.display = 'flex';
        if (secSolar) secSolar.style.display = 'flex';
        if (sidebarLinkGen) sidebarLinkGen.style.display = 'flex';
        if (sidebarLinkSolar) sidebarLinkSolar.style.display = 'flex';

        if (calibRowGen) calibRowGen.style.display = 'flex';
        if (calibRowSolar) calibRowSolar.style.display = 'flex';

        showToast("👑 <strong>Plan Premium Activo:</strong> Sistema Solar & Baterías desbloqueado.");
    }

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

    // Helper para actualizar estado de un item métrico
    function applyMetricStatus(boxId, iconId, valId, rangeId, status, safeMin, safeMax, unit) {
        const box = document.getElementById(boxId);
        const icon = document.getElementById(iconId);
        const val = document.getElementById(valId);
        const range = document.getElementById(rangeId);

        if (box) {
            box.classList.remove('critical-metric', 'warning-metric');
            if (status === 'CRITICAL') box.classList.add('critical-metric');
            else if (status === 'WARNING') box.classList.add('warning-metric');
        }

        if (val) {
            val.classList.remove('text-rose', 'text-amber');
            if (status === 'CRITICAL') val.classList.add('text-rose');
            else if (status === 'WARNING') val.classList.add('text-amber');
        }

        if (icon) {
            icon.classList.remove('text-rose', 'text-amber');
            if (status === 'CRITICAL') icon.classList.add('text-rose');
            else if (status === 'WARNING') icon.classList.add('text-amber');
        }

        if (range) {
            range.classList.remove('text-rose', 'text-amber');
            if (status === 'CRITICAL') {
                range.classList.add('text-rose');
                range.innerHTML = `Rango: <strong>Fuera (${safeMin !== null ? safeMin : ''} - ${safeMax !== null ? safeMax : ''} ${unit})</strong>`;
            } else if (status === 'WARNING') {
                range.classList.add('text-amber');
                range.innerHTML = `Rango: <strong>Atención (${safeMin !== null ? safeMin : ''} - ${safeMax !== null ? safeMax : ''} ${unit})</strong>`;
            } else {
                range.innerHTML = `Rango Óptimo: <strong>${safeMin !== null ? safeMin : ''} - ${safeMax !== null ? safeMax : ''} ${unit}</strong>`;
            }
        }
    }

    // ==========================================
    // A. TANQUE PRINCIPAL #1
    // ==========================================
    let isTank1Crit = false;
    let isTank1Warn = false;

    // 1. pH
    if (s.TANK_1_PH) {
        const item = s.TANK_1_PH;
        const valPH1 = document.getElementById('valPH1');
        if (valPH1) valPH1.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxPH1', 'iconPH1', 'valPH1', 'rangePH1', item.status, item.min_safe, item.max_safe, 'pH');
        if (item.status === 'CRITICAL') isTank1Crit = true;
        if (item.status === 'WARNING') isTank1Warn = true;

        const sliderPH = document.getElementById('sliderPH');
        const lblSliderPH = document.getElementById('lblSliderPH');
        if (sliderPH && document.activeElement !== sliderPH) sliderPH.value = item.current_value;
        if (lblSliderPH) lblSliderPH.textContent = `${item.current_value.toFixed(1)} pH`;
    }

    // 2. Nivel de Agua
    if (s.TANK_1_WATER_LEVEL) {
        const item = s.TANK_1_WATER_LEVEL;
        const valLvl1 = document.getElementById('valLevel1');
        const lblLiters1 = document.getElementById('lblLiters1');
        const fillLvl1 = document.getElementById('progressFillLevel1');

        if (valLvl1) valLvl1.textContent = Math.round(item.current_value);
        if (lblLiters1) lblLiters1.textContent = `% (${Math.round(item.current_value * 10)} L)`;
        if (fillLvl1) {
            fillLvl1.style.width = `${Math.min(100, Math.max(0, item.current_value))}%`;
            fillLvl1.className = item.status === 'CRITICAL' ? 'progress-fill red' : (item.status === 'WARNING' ? 'progress-fill red' : 'progress-fill green');
        }

        applyMetricStatus('metricBoxLevel1', 'iconLevel1', 'valLevel1', 'rangeLevel1', item.status, `> ${item.min_safe}`, '', '%');
        if (item.status === 'CRITICAL') isTank1Crit = true;
        if (item.status === 'WARNING') isTank1Warn = true;

        const sliderLevel = document.getElementById('sliderLevel');
        const lblSliderLevel = document.getElementById('lblSliderLevel');
        if (sliderLevel && document.activeElement !== sliderLevel) sliderLevel.value = item.current_value;
        if (lblSliderLevel) lblSliderLevel.textContent = `${Math.round(item.current_value)} %`;
    }

    // 3. EC Nutrientes
    if (s.TANK_1_EC) {
        const item = s.TANK_1_EC;
        const valEC1 = document.getElementById('valEC1');
        if (valEC1) valEC1.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxEC1', 'iconEC1', 'valEC1', 'rangeEC1', item.status, item.min_safe, item.max_safe, 'mS/cm');
        if (item.status === 'CRITICAL') isTank1Crit = true;
    }

    // 4. Temp Líquido
    if (s.TANK_1_TEMP_LIQUID) {
        const item = s.TANK_1_TEMP_LIQUID;
        const valTemp1 = document.getElementById('valTemp1');
        if (valTemp1) valTemp1.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxTemp1', 'iconTemp1', 'valTemp1', 'rangeTemp1', item.status, item.min_safe, item.max_safe, '°C');
        if (item.status === 'CRITICAL') isTank1Crit = true;
    }

    // 5. Caudal
    if (s.TANK_1_FLOW_RATE) {
        const item = s.TANK_1_FLOW_RATE;
        const valFlow1 = document.getElementById('valFlow1');
        if (valFlow1) valFlow1.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxFlow1', 'iconFlow1', 'valFlow1', 'rangeFlow1', item.status, item.min_safe, item.max_safe, 'L/min');
    }

    // 6. Oxígeno DO
    if (s.TANK_1_OXYGEN_DO) {
        const item = s.TANK_1_OXYGEN_DO;
        const valOxy1 = document.getElementById('valOxy1');
        if (valOxy1) valOxy1.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxOxy1', 'iconOxy1', 'valOxy1', 'rangeOxy1', item.status, `> ${item.min_safe}`, '', 'mg/L');
    }

    // Cabecera Tarjeta Tanque 1
    const tankCard1 = document.getElementById('tankCard1');
    const tankAvatar1 = document.getElementById('tankAvatar1');
    const tankPill1 = document.getElementById('tankStatusPill1');

    if (tankCard1) {
        tankCard1.classList.remove('critical-card', 'warning-card');
        if (isTank1Crit) tankCard1.classList.add('critical-card');
        else if (isTank1Warn) tankCard1.classList.add('warning-card');
    }
    if (tankAvatar1) {
        tankAvatar1.className = isTank1Crit ? 'tank-avatar-circle critical-avatar' : 'tank-avatar-circle';
    }
    if (tankPill1) {
        tankPill1.className = isTank1Crit ? 'status-indicator-pill crit' : (isTank1Warn ? 'status-indicator-pill warn' : 'status-indicator-pill opt');
        tankPill1.textContent = isTank1Crit ? 'Atención' : (isTank1Warn ? 'Alerta' : 'Óptimo');
    }

    // ==========================================
    // B. MICROCLIMA DEL INVERNADERO
    // ==========================================
    let isEnvCrit = false;
    let isEnvWarn = false;

    if (s.ENV_TEMP_AIR) {
        const item = s.ENV_TEMP_AIR;
        const valEnvTemp = document.getElementById('valEnvTemp');
        if (valEnvTemp) valEnvTemp.textContent = item.current_value.toFixed(1);
        applyMetricStatus('metricBoxEnvTemp', 'iconEnvTemp', 'valEnvTemp', 'rangeEnvTemp', item.status, item.min_safe, item.max_safe, '°C');
        if (item.status === 'CRITICAL') isEnvCrit = true;
        if (item.status === 'WARNING') isEnvWarn = true;

        const sliderTempAir = document.getElementById('sliderTempAir');
        const lblSliderTempAir = document.getElementById('lblSliderTempAir');
        if (sliderTempAir && document.activeElement !== sliderTempAir) sliderTempAir.value = item.current_value;
        if (lblSliderTempAir) lblSliderTempAir.textContent = `${item.current_value.toFixed(1)} °C`;
    }

    if (s.ENV_HUMIDITY) {
        const item = s.ENV_HUMIDITY;
        const valEnvHum = document.getElementById('valEnvHum');
        if (valEnvHum) valEnvHum.textContent = Math.round(item.current_value);
        applyMetricStatus('metricBoxEnvHum', 'iconEnvHum', 'valEnvHum', 'rangeEnvHum', item.status, item.min_safe, item.max_safe, '%');
        if (item.status === 'CRITICAL') isEnvCrit = true;
    }

    if (s.ENV_SOLAR_RAD) {
        const item = s.ENV_SOLAR_RAD;
        const valEnvRad = document.getElementById('valEnvRad');
        if (valEnvRad) valEnvRad.textContent = Math.round(item.current_value);
    }

    if (s.ENV_CO2) {
        const item = s.ENV_CO2;
        const valEnvCO2 = document.getElementById('valEnvCO2');
        if (valEnvCO2) valEnvCO2.textContent = Math.round(item.current_value);
    }

    if (s.ENV_AIR_FLOW) {
        const item = s.ENV_AIR_FLOW;
        const valEnvFlow = document.getElementById('valEnvFlow');
        if (valEnvFlow) valEnvFlow.textContent = item.current_value.toFixed(1);
    }

    // Cabecera Microclima
    const envCard = document.getElementById('envCard');
    const envAvatar = document.getElementById('envAvatar');
    const envStatusPill = document.getElementById('envStatusPill');
    if (envCard) {
        envCard.classList.remove('critical-card', 'warning-card');
        if (isEnvCrit) envCard.classList.add('critical-card');
        else if (isEnvWarn) envCard.classList.add('warning-card');
    }
    if (envAvatar) {
        envAvatar.className = isEnvCrit ? 'tank-avatar-circle critical-avatar' : 'tank-avatar-circle env-avatar';
    }
    if (envStatusPill) {
        envStatusPill.className = isEnvCrit ? 'status-indicator-pill crit' : (isEnvWarn ? 'status-indicator-pill warn' : 'status-indicator-pill opt');
        envStatusPill.textContent = isEnvCrit ? 'Atención' : (isEnvWarn ? 'Alerta' : 'Óptimo');
    }

    // ==========================================
    // C. GENERADOR & COMBUSTIBLE
    // ==========================================
    if (s.GEN_FUEL) {
        const item = s.GEN_FUEL;
        const valGenFuel = document.getElementById('valGenFuel');
        const lblLitersGenFuel = document.getElementById('lblLitersGenFuel');
        const fillGenFuel = document.getElementById('progressFillGenFuel');

        if (valGenFuel) valGenFuel.textContent = Math.round(item.current_value);
        if (lblLitersGenFuel) lblLitersGenFuel.textContent = `% (${Math.round(item.current_value)} L)`;
        if (fillGenFuel) {
            fillGenFuel.style.width = `${Math.min(100, Math.max(0, item.current_value))}%`;
            fillGenFuel.className = item.status === 'CRITICAL' ? 'progress-fill red' : 'progress-fill green';
        }
        applyMetricStatus('metricBoxGenFuel', 'iconGenFuel', 'valGenFuel', 'rangeGenFuel', item.status, `> ${item.min_safe}`, '', '%');

        const genCard = document.getElementById('genCard');
        const genPill = document.getElementById('genStatusPill');
        if (genCard) {
            if (item.status === 'CRITICAL') genCard.classList.add('critical-card');
            else genCard.classList.remove('critical-card');
        }
        if (genPill) {
            genPill.className = item.status === 'CRITICAL' ? 'status-indicator-pill crit' : 'status-indicator-pill opt';
            genPill.textContent = item.status === 'CRITICAL' ? 'Nivel Crítico' : 'Listo / En Espera';
        }

        const sliderFuel = document.getElementById('sliderFuel');
        const lblSliderFuel = document.getElementById('lblSliderFuel');
        if (sliderFuel && document.activeElement !== sliderFuel) sliderFuel.value = item.current_value;
        if (lblSliderFuel) lblSliderFuel.textContent = `${Math.round(item.current_value)} %`;
    }

    // ==========================================
    // D. SISTEMA SOLAR & BATERÍAS
    // ==========================================
    if (s.SOLAR_BATTERY_PCT) {
        const item = s.SOLAR_BATTERY_PCT;
        const valSolarBat = document.getElementById('valSolarBat');
        const fillSolarBat = document.getElementById('progressFillSolarBat');

        if (valSolarBat) valSolarBat.textContent = Math.round(item.current_value);
        if (fillSolarBat) {
            fillSolarBat.style.width = `${Math.min(100, Math.max(0, item.current_value))}%`;
            fillSolarBat.className = item.status === 'CRITICAL' ? 'progress-fill red' : 'progress-fill green';
        }
        applyMetricStatus('metricBoxSolarBat', 'iconSolarBat', 'valSolarBat', 'rangeSolarBat', item.status, `> ${item.min_safe}`, '', '%');

        const solarCard = document.getElementById('solarCard');
        const solarPill = document.getElementById('solarStatusPill');
        if (solarCard) {
            if (item.status === 'CRITICAL') solarCard.classList.add('critical-card');
            else solarCard.classList.remove('critical-card');
        }
        if (solarPill) {
            solarPill.className = item.status === 'CRITICAL' ? 'status-indicator-pill crit' : 'status-indicator-pill opt';
            solarPill.textContent = item.status === 'CRITICAL' ? 'Batería Crítica' : '100% Autosuficiente';
        }

        const sliderSolarBat = document.getElementById('sliderSolarBat');
        const lblSliderSolarBat = document.getElementById('lblSliderSolarBat');
        if (sliderSolarBat && document.activeElement !== sliderSolarBat) sliderSolarBat.value = item.current_value;
        if (lblSliderSolarBat) lblSliderSolarBat.textContent = `${Math.round(item.current_value)} %`;
    }

    // 3. Renderizar Alertas Activas en el Centro de Alertas
    renderAlertsFeed(data.active_alerts || []);
}

// -----------------------------------------------------------------------------
// 3. RENDERIZADO Y RESOLUCIÓN INDIVIDUAL DE ALERTAS (POSTGRESQL)
// -----------------------------------------------------------------------------
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
                            <h4 class="alert-item-title">Todos los sistemas en rango óptimo</h4>
                        </div>
                    </div>
                    <span class="badge-status-pill badge-resolved">NORMAL</span>
                </div>
                <p class="alert-description" style="color: #15803d; font-weight: 600;">
                    La solución nutritiva y el microclima están estables.
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

        // Procesar receta de asistencia pasiva si existe
        let recipeHTML = '';
        if (a.pasos_resolucion) {
            const lines = a.pasos_resolucion.split('\n').filter(l => l.trim().length > 0);
            let headerTitle = 'Receta Correctiva Calculada';
            let doseBadge = '';
            const stepItems = [];

            lines.forEach(l => {
                if (l.startsWith('Receta Correctiva:')) {
                    headerTitle = l.replace('Receta Correctiva:', '').trim();
                } else if (l.includes('Dosis calculada:') || l.includes('Reposición estimada:') || l.includes('Dilución requerida:') || l.includes('Carga requerida:')) {
                    doseBadge = l.replace(/•/g, '').trim();
                } else if (l.includes('• Paso') || l.startsWith('Paso')) {
                    const cleanText = l.replace(/•/g, '').trim();
                    stepItems.push(cleanText);
                } else if (l.startsWith('•')) {
                    stepItems.push(l.replace(/•/g, '').trim());
                }
            });

            recipeHTML = `
                <div class="recipe-accordion">
                    <button class="btn-toggle-recipe" onclick="toggleRecipe('${a.id}')">
                        <span><i class="fa-solid fa-clipboard-list" style="color: #10b981; margin-right: 6px;"></i> Receta de Asistencia Pasiva</span>
                        <i class="fa-solid fa-chevron-down" id="recipe_chevron_${a.id}"></i>
                    </button>
                    <div class="recipe-box" id="recipe_box_${a.id}">
                        <div class="recipe-header-row">
                            <span class="recipe-title"><i class="fa-solid fa-flask-vial text-emerald"></i> ${headerTitle}</span>
                            ${doseBadge ? `<span class="recipe-badge-dose">${doseBadge}</span>` : ''}
                        </div>
                        <div class="recipe-steps-list">
                            ${stepItems.map((step, idx) => `
                                <div class="recipe-step-item">
                                    <span class="recipe-step-num">${idx + 1}</span>
                                    <span>${step}</span>
                                </div>
                            `).join('')}
                        </div>
                        <div class="recipe-disclaimer">
                            <i class="fa-solid fa-circle-info"></i>
                            <span>Asistencia Pasiva: El sistema no acciona motores automáticamente. Siga los pasos manuales calculados.</span>
                        </div>
                        <button class="btn-complete-recipe" onclick="resolveSingleAlert('${a.id}', '${a.sensor_code}')">
                            <i class="fa-solid fa-check"></i>
                            <span>Marcar Acción Realizada y Normalizar</span>
                        </button>
                    </div>
                </div>
            `;
        }

        // Card completa en el Panel de Acción
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
                
                ${recipeHTML}

                
            </div>
        `;
    });

    alertsFeed.innerHTML = html;
}

function toggleRecipe(alertId) {
    const box = document.getElementById(`recipe_box_${alertId}`);
    const chev = document.getElementById(`recipe_chevron_${alertId}`);
    if (box) {
        box.classList.toggle('open');
        if (chev) {
            chev.className = box.classList.contains('open') ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
        }
    }
}

// Resolver ÚNICAMENTE la alerta seleccionada
async function resolveSingleAlert(alertId, sensorCode) {
    const tier = getCurrentTier();
    try {
        const res = await fetch('/api/v1/simulation/resolve-alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                alert_id: alertId,
                sensor_code: sensorCode,
                tier: tier
            })
        });

        if (res.ok) {
            const data = await res.json();
            showToast(`✅ <strong>Alerta resuelta:</strong> ${sensorCode ? sensorCode.replace(/_/g, ' ') : 'Sensor'} restablecido a valores óptimos.`);
            // Refrescar estado en vivo (las demás alertas permanecen intactas)
            fetchLiveState();
        }
    } catch (err) {
        console.error("Error al resolver alerta individual:", err);
    }
}

// -----------------------------------------------------------------------------
// 4. MODIFICACIÓN DE PARÁMETROS EN VIVO Y CALIBRACIÓN (SLIDERS & PRESETS)
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
    }, 200);
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

// -----------------------------------------------------------------------------
// 5. CONTROL DE MODALES Y MENÚS
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

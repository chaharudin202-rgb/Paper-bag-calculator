import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go
from PIL import Image
import numpy as np
import math
import os
from io import BytesIO

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Paper Bag Calculator Pro",
    page_icon="🛍️",
    layout="wide"
)

# ==========================================
# SESSION STATE INIT
# ==========================================
if 'cost_items' not in st.session_state:
    st.session_state.cost_items = [
        {"nama": "Kertas Ivory 250gr", "basis": "Per Lembar Plano", "harga": 5000, "batch": 1},
        {"nama": "Ongkos Cetak Offset", "basis": "Per Batch (Kelipatan Pcs)", "harga": 450000, "batch": 2000},
        {"nama": "Tali Kur & Pasang", "basis": "Per Pcs Tas", "harga": 700, "batch": 1}
    ]

# ==========================================
# SIDEBAR - INPUTS
# ==========================================
st.sidebar.title("🛍️ Paper Bag Calculator")
st.sidebar.markdown("---")

st.sidebar.header("📏 Dimensi Produk")
P = st.sidebar.number_input("Panjang (P) cm", value=15.0, min_value=1.0, step=0.5)
L = st.sidebar.number_input("Lebar (L) cm", value=8.0, min_value=1.0, step=0.5)
T = st.sidebar.number_input("Tinggi (T) cm", value=20.0, min_value=1.0, step=0.5)
lem = st.sidebar.number_input("Lidah Lem (cm)", value=2.0, min_value=0.5, step=0.5)
top_lip = st.sidebar.number_input("Lipatan Atas (cm)", value=2.0, min_value=0.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("📦 Produksi")
qty = st.sidebar.number_input("Quantity Order (pcs)", value=1000, min_value=1, step=100)

st.sidebar.markdown("---")
st.sidebar.header("📄 Ukuran Plano")
plano_w = st.sidebar.number_input("Lebar Plano (cm)", value=109.0, min_value=10.0, step=1.0)
plano_h = st.sidebar.number_input("Tinggi Plano (cm)", value=79.0, min_value=10.0, step=1.0)

# Margin Plano
st.sidebar.subheader("Margin Bahan (cm)")
m_top = st.sidebar.number_input("Margin Atas", value=1.0, min_value=0.0, step=0.5)
m_bottom = st.sidebar.number_input("Margin Bawah", value=1.0, min_value=0.0, step=0.5)
m_left = st.sidebar.number_input("Margin Kiri", value=1.5, min_value=0.0, step=0.5)
m_right = st.sidebar.number_input("Margin Kanan", value=1.5, min_value=0.0, step=0.5)

# ==========================================
# CALCULATIONS (BACKEND)
# ==========================================

# Pattern dimensions
pola_w_net = lem + (2 * L) + (2 * P)
pola_h_net = T + top_lip + (0.5 * P)
area_cm2_per_pcs = pola_w_net * pola_h_net

# Pattern with margins
unit_w = pola_w_net + m_left + m_right
unit_h = pola_h_net + m_top + m_bottom

# Plano optimization
def optimize_plano(PL_W, PL_H, U_W, U_H):
    def check_layout(W_canvas, H_canvas, W_item, H_item):
        cols = W_canvas // W_item
        rows = H_canvas // H_item
        rects = []
        for r in range(int(rows)):
            for c in range(int(cols)):
                rects.append({
                    'x': c * W_item, 
                    'y': r * H_item, 
                    'w': W_item, 
                    'h': H_item, 
                    'rot': False
                })
        
        # Remainder space (rotated)
        sisa_w = W_canvas - (cols * W_item)
        if sisa_w >= H_item:
            c_sisa = sisa_w // H_item
            r_sisa = H_canvas // W_item
            for r in range(int(r_sisa)):
                for c in range(int(c_sisa)):
                    rects.append({
                        'x': (cols * W_item) + (c * H_item),
                        'y': r * W_item,
                        'w': H_item,
                        'h': W_item,
                        'rot': True
                    })
        return rects
    
    res1 = check_layout(PL_W, PL_H, U_W, U_H)
    res2 = check_layout(PL_H, PL_W, U_W, U_H)
    
    if len(res1) >= len(res2):
        return res1, PL_W, PL_H
    else:
        return res2, PL_H, PL_W

layout_positions, final_plano_w, final_plano_h = optimize_plano(plano_w, plano_h, unit_w, unit_h)
pcs_per_plano = len(layout_positions)

if pcs_per_plano == 0:
    st.error("⚠️ Ukuran pola lebih besar dari plano! Sesuaikan dimensi atau ukuran plano.")
    st.stop()

total_plano_req = math.ceil(qty / pcs_per_plano)
efficiency = (pcs_per_plano * unit_w * unit_h) / (final_plano_w * final_plano_h) * 100

# Cost calculation
total_production_cost = 0
breakdown_biaya = []

for item in st.session_state.cost_items:
    subtotal = 0
    if item['basis'] == "Per Pesanan (Tetap)":
        subtotal = item['harga']
    elif item['basis'] == "Per Lembar Plano":
        subtotal = item['harga'] * total_plano_req
    elif item['basis'] == "Per Pcs Tas":
        subtotal = item['harga'] * qty
    elif item['basis'] == "Per Area (cm2)":
        subtotal = item['harga'] * area_cm2_per_pcs * qty
    elif item['basis'] == "Per Batch (Kelipatan Pcs)":
        jumlah_batch = math.ceil(qty / item['batch'])
        subtotal = item['harga'] * jumlah_batch
    
    total_production_cost += subtotal
    breakdown_biaya.append({
        "Item": item['nama'],
        "Basis": item['basis'],
        "Subtotal (Rp)": f"{subtotal:,.0f}"
    })

# ==========================================
# MAIN APP - TABS
# ==========================================
st.title("🛍️ Paper Bag Production Calculator")
st.markdown("**Professional Paper Bag Cost Estimation & Pattern Generator**")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💰 Pricing", 
    "📐 Pattern 2D", 
    "📦 Plano Layout", 
    "🎨 3D Mockup",
    "⚙️ Settings"
])

# ==========================================
# TAB 1: PRICING
# ==========================================
with tab1:
    st.header("💰 Kalkulasi Harga Produksi")
    
    # Quick Info
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pattern Size", f"{pola_w_net:.1f} × {pola_h_net:.1f} cm")
    col2.metric("Pcs/Plano", f"{pcs_per_plano} pcs")
    col3.metric("Total Plano", f"{total_plano_req} sheets")
    col4.metric("Efficiency", f"{efficiency:.1f}%")
    
    st.markdown("---")
    
    # Profit Margin
    st.subheader("📈 Profit Margin")
    col_m1, col_m2 = st.columns(2)
    
    margin_type = col_m1.radio(
        "Tipe Margin",
        ["Persentase (%)", "Fix Total (Rp)", "Fix per Pcs (Rp)"]
    )
    
    margin_val = col_m2.number_input("Nilai Margin", value=30.0 if margin_type == "Persentase (%)" else 500000.0, min_value=0.0)
    
    # Calculate profit
    if margin_type == "Persentase (%)":
        total_profit = total_production_cost * (margin_val / 100)
    elif margin_type == "Fix Total (Rp)":
        total_profit = margin_val
    else:  # Fix per Pcs
        total_profit = margin_val * qty
    
    total_selling_price = total_production_cost + total_profit
    unit_price = total_selling_price / qty
    
    st.markdown("---")
    
    # Results
    st.subheader("📊 Hasil Kalkulasi")
    res1, res2, res3, res4 = st.columns(4)
    
    res1.metric(
        "Biaya Produksi",
        f"Rp {total_production_cost:,.0f}",
        help="Total biaya material & produksi"
    )
    
    res2.metric(
        "Profit",
        f"Rp {total_profit:,.0f}",
        delta=f"{(total_profit/total_production_cost*100):.1f}% margin"
    )
    
    res3.metric(
        "Harga Jual",
        f"Rp {total_selling_price:,.0f}",
        help="Total yang dibayar customer"
    )
    
    res4.metric(
        "Harga per Pcs",
        f"Rp {unit_price:,.0f}"
    )
    
    # Breakdown
    with st.expander("📋 Detail Breakdown Biaya"):
        st.table(breakdown_biaya)

# ==========================================
# TAB 2: PATTERN 2D
# ==========================================
with tab2:
    st.header("📐 Pola Paper Bag 2D")
    
    if st.button("🎨 Generate Pattern", key="gen_pattern"):
        with st.spinner("Generating 2D pattern..."):
            # Coordinates
            x = [0]
            for width in [lem, L, P, L, P]:
                x.append(x[-1] + width)
            
            y_actual_top = T + top_lip
            y_top_fold = T
            y_green = 0.5 * L
            y_base = 0
            y_bottom = -(0.5 * P)
            
            y_hole_upper = T + (top_lip / 2)
            y_hole_lower = T - (top_lip / 2)
            
            v_mids = [(x[1] + x[2]) / 2, (x[3] + x[4]) / 2]
            p_panels = [(x[2], x[3]), (x[4], x[5])]
            
            # Plot
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Vertical lines
            for val_x in x:
                ax.plot([val_x, val_x], [y_bottom, y_actual_top], color='black', lw=1)
            
            # Horizontal lines
            ax.plot([x[0], x[-1]], [y_actual_top, y_actual_top], color='black', lw=1.5)
            ax.plot([x[0], x[-1]], [y_top_fold, y_top_fold], color='black', ls='--', lw=1.2, label='Fold line (T)')
            ax.plot([x[0], x[-1]], [y_bottom, y_bottom], color='black', lw=1.5)
            ax.plot([x[0], x[-1]], [y_base, y_base], color='gray', ls=':', alpha=0.5)
            ax.plot([x[0], x[-1]], [y_green, y_green], color='green', ls='--', lw=1, label='Gusset')
            
            # Gusset verticals
            ax.plot([v_mids[0], v_mids[0]], [y_green, y_actual_top], color='blue', lw=1.5)
            ax.plot([v_mids[1], v_mids[1]], [y_green, y_actual_top], color='blue', lw=1.5)
            
            # Holes
            hole_size = 0.35
            for p_start, p_end in p_panels:
                h1_x = p_start + (0.25 * P)
                h2_x = p_start + (0.75 * P)
                for h_x in [h1_x, h2_x]:
                    up_circ = plt.Circle((h_x, y_hole_upper), hole_size, color='blue', fill=False, lw=1.5)
                    low_circ = plt.Circle((h_x, y_hole_lower), hole_size, color='blue', fill=False, lw=1.5)
                    ax.add_patch(up_circ)
                    ax.add_patch(low_circ)
            
            # Diagonals
            p_mid1 = (x[2] + x[3]) / 2
            p_mid2 = (x[4] + x[5]) / 2
            
            ax.plot([v_mids[0], x[0]], [y_green, y_green - (v_mids[0] - x[0])], color='red', lw=2)
            ax.plot([v_mids[0], p_mid1], [y_green, y_bottom], color='red', lw=2)
            ax.plot([p_mid1, v_mids[1]], [y_bottom, y_green], color='red', lw=2)
            ax.plot([v_mids[1], p_mid2], [y_green, y_bottom], color='red', lw=2)
            ax.plot([p_mid2, x[5]], [y_bottom, y_base], color='red', lw=2)
            
            ax.set_aspect('equal')
            ax.set_title(f"Paper Bag Pattern: {P}×{L}×{T} cm", fontsize=14, fontweight='bold')
            ax.set_xlabel("Width (cm)")
            ax.set_ylabel("Height (cm)")
            ax.grid(True, which='both', linestyle=':', alpha=0.3)
            ax.legend()
            
            st.pyplot(fig)
            
            st.success(f"✅ Pattern generated: {pola_w_net:.1f} × {pola_h_net:.1f} cm")

# ==========================================
# TAB 3: PLANO LAYOUT
# ==========================================
with tab3:
    st.header("📦 Optimasi Layout Plano")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Pieces per Plano", f"{pcs_per_plano} pcs")
    col2.metric("Total Plano Needed", f"{total_plano_req} sheets")
    col3.metric("Material Efficiency", f"{efficiency:.1f}%")
    
    if st.button("🎨 Generate Layout", key="gen_plano"):
        with st.spinner("Optimizing layout..."):
            fig, ax = plt.subplots(figsize=(14, 10))
            ax.set_aspect('equal')
            
            # Plano outline
            ax.add_patch(patches.Rectangle(
                (0, 0), final_plano_w, final_plano_h,
                lw=3, edgecolor='black', facecolor='white'
            ))
            
            # Draw each piece
            for p in layout_positions:
                # Material area (with margin)
                ax.add_patch(patches.Rectangle(
                    (p['x'], p['y']), p['w'], p['h'],
                    lw=1, edgecolor='gray', ls='--',
                    facecolor='#f0f0f0', alpha=0.5
                ))
                
                # Print area (net)
                if not p['rot']:
                    inner_x = p['x'] + m_left
                    inner_y = p['y'] + m_bottom
                    inner_w, inner_h = pola_w_net, pola_h_net
                    color = 'skyblue'
                else:
                    inner_x = p['x'] + m_bottom
                    inner_y = p['y'] + m_left
                    inner_w, inner_h = pola_h_net, pola_w_net
                    color = 'orange'
                
                ax.add_patch(patches.Rectangle(
                    (inner_x, inner_y), inner_w, inner_h,
                    lw=1, edgecolor='blue', facecolor=color, alpha=0.7
                ))
            
            ax.set_xlim(-5, final_plano_w + 5)
            ax.set_ylim(-5, final_plano_h + 5)
            ax.set_title(f"Plano Layout: {pcs_per_plano} pcs on {final_plano_w}×{final_plano_h} cm sheet", fontsize=14, fontweight='bold')
            ax.set_xlabel("Width (cm)")
            ax.set_ylabel("Height (cm)")
            
            st.pyplot(fig)
            
            st.info(f"💡 Blue = Normal orientation | Orange = Rotated 90°")
            st.success(f"✅ Efficiency: {efficiency:.1f}% | Waste: {100-efficiency:.1f}%")

# ==========================================
# TAB 4: 3D MOCKUP
# ==========================================
with tab4:
    st.header("🎨 3D Mockup Preview")
    
    col1, col2 = st.columns(2)
    bag_color = col1.color_picker("Bag Color", "#D3D3D3")
    handle_color = col2.color_picker("Handle Color", "#222222")
    
    if st.button("🎨 Generate 3D Mockup", key="gen_3d"):
        with st.spinner("Rendering 3D mockup..."):
            # Geometry
            pinch = (L / 2) * 0.9
            z_hole = T - 2.0
            
            def get_v(z_h, p_v):
                return [
                    [0, 0, z_h], [P, 0, z_h],
                    [P - p_v, L/2, z_h], [P, L, z_h],
                    [0, L, z_h], [p_v, L/2, z_h]
                ]
            
            v_pts = get_v(0, pinch*0.5) + get_v(T, pinch)
            vx = [v[0] for v in v_pts]
            vy = [v[1] for v in v_pts]
            vz = [v[2] for v in v_pts]
            
            fig = go.Figure()
            
            # Body mesh
            def get_f(off_l, off_h):
                f = []
                for s in range(5):
                    f.extend([
                        [off_l+s, off_l+s+1, off_h+s+1],
                        [off_l+s, off_h+s+1, off_h+s]
                    ])
                f.extend([
                    [off_l+5, off_l+0, off_h+0],
                    [off_l+5, off_h+0, off_h+5]
                ])
                return f
            
            faces = get_f(0, 6)
            
            fig.add_trace(go.Mesh3d(
                x=vx, y=vy, z=vz,
                i=[f[0] for f in faces],
                j=[f[1] for f in faces],
                k=[f[2] for f in faces],
                color=bag_color,
                opacity=1.0,
                flatshading=True,
                name='Bag'
            ))
            
            # Handles
            def handle(y_p, name):
                hx, hz = [], []
                for s in range(21):
                    t = s / 20
                    hx.append(P*0.25 + (P*0.5)*t)
                    hz.append(z_hole + 6 * math.sin(math.pi * t))
                fig.add_trace(go.Scatter3d(
                    x=hx, y=[y_p]*21, z=hz,
                    mode='lines',
                    line=dict(color=handle_color, width=7),
                    name=name
                ))
            
            handle(0, 'Front Handle')
            handle(L, 'Back Handle')
            
            # Holes
            fig.add_trace(go.Scatter3d(
                x=[P*0.25, P*0.75, P*0.25, P*0.75],
                y=[-0.02, -0.02, L+0.02, L+0.02],
                z=[z_hole]*4,
                mode='markers',
                marker=dict(size=8, color='black'),
                name='Holes'
            ))
            
            # Wireframe
            edge_pairs = [
                (0,1),(1,2),(2,3),(3,4),(4,5),(5,0),
                (6,7),(7,8),(8,9),(9,10),(10,11),(11,6),
                (0,6),(1,7),(2,8),
                (3,9),(4,10),(5,11)
            ]
            ex, ey, ez = [], [], []
            for p1, p2 in edge_pairs:
                ex.extend([vx[p1], vx[p2], None])
                ey.extend([vy[p1], vy[p2], None])
                ez.extend([vz[p1], vz[p2], None])
            
            fig.add_trace(go.Scatter3d(
                x=ex, y=ey, z=ez,
                mode='lines',
                line=dict(color='black', width=1),
                showlegend=False
            ))
            
            fig.update_layout(
                scene=dict(
                    aspectmode='data',
                    camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
                ),
                title=f"3D Mockup: {P}×{L}×{T} cm"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.success("✅ 3D mockup generated!")

# ==========================================
# TAB 5: SETTINGS
# ==========================================
with tab5:
    st.header("⚙️ Cost Items Management")
    
    with st.expander("➕ Add New Cost Item", expanded=False):
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        
        new_nama = col1.text_input("Item Name", placeholder="e.g., Lamination")
        new_basis = col2.selectbox(
            "Calculation Basis",
            ["Per Pesanan (Tetap)", "Per Lembar Plano", "Per Pcs Tas", "Per Area (cm2)", "Per Batch (Kelipatan Pcs)"]
        )
        new_harga = col3.number_input("Price (Rp)", min_value=0.0, value=0.0, format="%.2f")
        new_batch = col4.number_input("Batch Size (Pcs)", min_value=1, value=1)
        
        if st.button("➕ Add Item"):
            if new_nama:
                st.session_state.cost_items.append({
                    "nama": new_nama,
                    "basis": new_basis,
                    "harga": new_harga,
                    "batch": new_batch
                })
                st.success(f"✅ Added: {new_nama}")
                st.rerun()
            else:
                st.error("❌ Item name is required!")
    
    st.markdown("---")
    st.subheader("📋 Current Cost Items")
    
    for i, item in enumerate(st.session_state.cost_items):
        col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 1, 1])
        
        col1.write(f"**{item['nama']}**")
        col2.write(f"_{item['basis']}_")
        col3.write(f"Rp {item['harga']:,.0f}")
        
        if col4.button("✏️", key=f"edit_{i}"):
            st.info("Edit feature coming soon!")
        
        if col5.button("🗑️", key=f"del_{i}"):
            st.session_state.cost_items.pop(i)
            st.rerun()

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Paper Bag Calculator Pro</strong> v1.0 | Built with Streamlit</p>
    <p>For business inquiries: <a href='mailto:your@email.com'>chahatudin202@gmail.com</a></p>
</div>
""", unsafe_allow_html=True)
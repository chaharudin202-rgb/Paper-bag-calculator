import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go
import numpy as np
import math
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
        {"name": "Overhead Cost", "basis": "Fixed per Order", "price": 100000, "batch": 1},
        {"name": "Packing Cost", "basis": "Per Pcs Bag", "price": 500, "batch": 1}
    ]

if 'profit_margin' not in st.session_state:
    st.session_state.profit_margin = 30.0

# ==========================================
# HELPER FUNCTIONS
# ==========================================

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

def calculate_costs(cost_items, qty, total_plano_req, area_cm2_per_pcs):
    """Calculate total production cost with safety check"""
    if not cost_items or len(cost_items) == 0:
        return 0, []
    
    total_cost = 0
    breakdown = []
    
    for item in cost_items:
        subtotal = 0
        if item['basis'] == "Fixed per Order":
            subtotal = item['price']
        elif item['basis'] == "Per Plano Sheet":
            subtotal = item['price'] * total_plano_req
        elif item['basis'] == "Per Pcs Bag":
            subtotal = item['price'] * qty
        elif item['basis'] == "Per Area (cm2)":
            subtotal = item['price'] * area_cm2_per_pcs * qty
        elif item['basis'] == "Per Batch (Multiple Pcs)":
            jumlah_batch = math.ceil(qty / item['batch']) if item['batch'] > 0 else 0
            subtotal = item['price'] * jumlah_batch
        
        total_cost += subtotal
        breakdown.append({
            "Item": item['name'],
            "Basis": item['basis'],
            "Subtotal ($)": f"{subtotal:,.0f}"
        })
    
    return total_cost, breakdown

def generate_3d_mockup(P, L, T, bag_color, handle_color, conv, unit):
    """Generate 3D mockup figure"""
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
        (0,6),(1,7),(2,8),(3,9),(4,10),(5,11)
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
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            xaxis_title=f"Length ({unit})",
            yaxis_title=f"Width ({unit})",
            zaxis_title=f"Height ({unit})"
        ),
        title=f"3D Mockup: {P/conv:.2f}×{L/conv:.2f}×{T/conv:.2f} {unit}",
        height=500
    )
    
    return fig

# ==========================================
# MAIN HEADER
# ==========================================
st.title("🛍️ Paper Bag Calculator Pro")
st.markdown("**Professional Tool for Paper Bag Sellers & Buyers**")

# Banner
st.info("""
💡 **How this works:**
- **Tab 1 (Seller Dashboard):** Manage production config, costs, and view profit margins.
- **Tab 2 (Customer View):** Customer inputs dimensions & quantity here. View Price & Mockup.
""")

st.markdown("---")

# ==========================================
# TABS
# ==========================================
tab1, tab2 = st.tabs([
    "💰 Seller Dashboard",
    "👤 Customer View (Inputs)"
])

# ==========================================
# COLLECT INPUTS (LOGIC FLOW)
# ==========================================
# Kita mengambil input dari Customer Tab (Tab 2) terlebih dahulu agar bisa digunakan di Tab 1

with tab2:
    st.header("👤 Customer Inputs")
    c_col1, c_col2 = st.columns(2)
    
    with c_col1:
        st.subheader("📏 Unit & Dimensions")
        unit_system = st.radio("Measurement Unit", ["Metric (cm)", "Imperial (inch)"], index=0, horizontal=True)
        unit = "cm" if unit_system == "Metric (cm)" else "inch"
        conv = 2.54 if unit == "inch" else 1.0
        
        P = st.number_input(f"Length (P) {unit}", value=15.0/conv, min_value=1.0/conv, step=0.5/conv, format="%.2f", key="main_P") * conv
        L = st.number_input(f"Width (L) {unit}", value=8.0/conv, min_value=1.0/conv, step=0.5/conv, format="%.2f", key="main_L") * conv
        T = st.number_input(f"Height (T) {unit}", value=20.0/conv, min_value=1.0/conv, step=0.5/conv, format="%.2f", key="main_T") * conv
        
    with c_col2:
        st.subheader("📦 Order Quantity")
        qty = st.number_input("Quantity (pcs)", value=1000, min_value=1, step=100, key="main_qty")

# ==========================================
# TAB 1: SELLER DASHBOARD (LOGIC & DISPLAY)
# ==========================================
with tab1:
    st.header("👨‍💼 Seller Configuration & Costs")
    
    # SELLER CONFIGURATION INPUTS
    with st.expander("⚙️ Production Configuration (Plano, Margins, Fold)", expanded=True):
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            st.markdown(f"**📄 Plano Size ({unit})**")
            plano_w = st.number_input(f"Plano Width", value=109.0/conv, min_value=10.0/conv, step=1.0/conv, format="%.2f") * conv
            plano_h = st.number_input(f"Plano Height", value=79.0/conv, min_value=10.0/conv, step=1.0/conv, format="%.2f") * conv
            
        with col_s2:
            st.markdown(f"**📐 Folds & Glue ({unit})**")
            lem = st.number_input(f"Glue Tab", value=2.0/conv, min_value=0.5/conv, step=0.5/conv, format="%.2f") * conv
            top_lip = st.number_input(f"Top Fold", value=2.0/conv, min_value=0.0, step=0.5/conv, format="%.2f") * conv
            
        with col_s3:
            st.markdown(f"**✂️ Print Margins ({unit})**")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_top = st.number_input("Top", value=1.0/conv, min_value=0.0, step=0.5/conv, format="%.2f") * conv
                m_bottom = st.number_input("Bottom", value=1.0/conv, min_value=0.0, step=0.5/conv, format="%.2f") * conv
            with col_m2:
                m_left = st.number_input("Left", value=1.5/conv, min_value=0.0, step=0.5/conv, format="%.2f") * conv
                m_right = st.number_input("Right", value=1.5/conv, min_value=0.0, step=0.5/conv, format="%.2f") * conv
    
    # CALCULATIONS
    pola_w_net = lem + (2 * L) + (2 * P)
    pola_h_net = T + top_lip + (0.5 * P)
    area_cm2_per_pcs = pola_w_net * pola_h_net
    
    unit_w = pola_w_net + m_left + m_right
    unit_h = pola_h_net + m_top + m_bottom
    
    layout_positions, final_plano_w, final_plano_h = optimize_plano(plano_w, plano_h, unit_w, unit_h)
    pcs_per_plano = len(layout_positions)
    
    if pcs_per_plano == 0:
        st.error("⚠️ Pattern size exceeds plano! Please adjust dimensions or plano size.")
        st.stop()
    
    total_plano_req = math.ceil(qty / pcs_per_plano)
    efficiency = (pcs_per_plano * unit_w * unit_h) / (final_plano_w * final_plano_h) * 100
    
    # Calculate costs with safety check
    total_production_cost, breakdown_biaya = calculate_costs(
        st.session_state.cost_items, 
        qty, 
        total_plano_req, 
        area_cm2_per_pcs
    )
    
    # PROFIT MARGIN
    st.markdown("---")
    with st.expander("📈 Profit Margin Settings", expanded=True):
        col_m1, col_m2 = st.columns(2)
        
        margin_type = col_m1.radio(
            "Margin Type",
            ["Percentage (%)", "Fixed Total ($)", "Fixed per Pcs ($)"]
        )
        
        if margin_type == "Percentage (%)":
            default_val = st.session_state.profit_margin
        else:
            default_val = 500000.0
        
        margin_val = col_m2.number_input("Margin Value", value=default_val, min_value=0.0)
        
        if margin_type == "Percentage (%)":
            st.session_state.profit_margin = margin_val
            total_profit = total_production_cost * (margin_val / 100)
        elif margin_type == "Fixed Total ($)":
            total_profit = margin_val
        else:
            total_profit = margin_val * qty
    
    total_selling_price = total_production_cost + total_profit
    unit_price = total_selling_price / qty if qty > 0 else 0
    
    # KEY METRICS
    st.markdown("---")
    st.subheader("📊 Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "Production Cost",
        f"$ {total_production_cost:,.0f}",
        help="Your total cost"
    )
    
    col2.metric(
        "Profit",
        f"$ {total_profit:,.0f}",
        delta=f"{(total_profit/total_production_cost*100) if total_production_cost > 0 else 0:.1f}% margin"
    )
    
    col3.metric(
        "Customer Pays (Total)",
        f"$ {total_selling_price:,.0f}",
        help="What buyer sees"
    )
    
    col4.metric(
        "Price per Pcs",
        f"$ {unit_price:,.0f}",
        help="Customer price per piece"
    )
    
    # COST ITEMS MANAGEMENT
    st.markdown("---")
    with st.expander("💰 Manage Cost Items", expanded=True):
        # Add new item
        st.subheader("➕ Add Cost Item")
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        
        new_name = col1.text_input("Item Name", placeholder="e.g., Paper Material", key="new_item_name")
        new_basis = col2.selectbox(
            "Calculation Basis",
            ["Fixed per Order", "Per Plano Sheet", "Per Pcs Bag", "Per Area (cm2)", "Per Batch (Multiple Pcs)"],
            key="new_item_basis"
        )
        new_price = col3.number_input("Price ($)", min_value=0.0, value=0.0, format="%.2f", key="new_item_price")
        new_batch = col4.number_input("Batch Size", min_value=1, value=1, key="new_item_batch")
        
        if st.button("➕ Add Item"):
            if new_name.strip():
                st.session_state.cost_items.append({
                    "name": new_name,
                    "basis": new_basis,
                    "price": new_price,
                    "batch": new_batch
                })
                st.success(f"✅ Added: {new_name}")
                st.rerun()
            else:
                st.error("❌ Item name is required!")
        
        st.markdown("---")
        
        # Current items
        st.subheader("📋 Current Cost Items")
        
        if len(st.session_state.cost_items) == 0:
            st.warning("⚠️ No cost items. Add at least one item above to calculate costs.")
        else:
            for i, item in enumerate(st.session_state.cost_items):
                col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
                
                col1.write(f"**{item['name']}**")
                col2.write(f"_{item['basis']}_")
                col3.write(f"$ {item['price']:,.0f}")
                
                if col4.button("🗑️", key=f"del_{i}"):
                    st.session_state.cost_items.pop(i)
                    st.rerun()
        
        # Detailed breakdown
        if len(breakdown_biaya) > 0:
            st.markdown("---")
            st.subheader("📋 Cost Breakdown")
            st.table(breakdown_biaya)
    
    # MATERIAL EFFICIENCY
    st.markdown("---")
    with st.expander("📦 Material Efficiency & Layout", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Pieces per Plano", f"{pcs_per_plano} pcs")
        col2.metric("Total Plano Needed", f"{total_plano_req} sheets")
        col3.metric("Material Efficiency", f"{efficiency:.1f}%")
        
        if st.button("🎨 Show Plano Layout", key="show_plano"):
            with st.spinner("Generating layout..."):
                fig, ax = plt.subplots(figsize=(14, 10))
                ax.set_aspect('equal')
                
                ax.add_patch(patches.Rectangle(
                    (0, 0), final_plano_w/conv, final_plano_h/conv,
                    lw=3, edgecolor='black', facecolor='white'
                ))
                
                for p in layout_positions:
                    ax.add_patch(patches.Rectangle(
                        (p['x']/conv, p['y']/conv), p['w']/conv, p['h']/conv,
                        lw=1, edgecolor='gray', ls='--',
                        facecolor='#f0f0f0', alpha=0.5
                    ))
                    
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
                        (inner_x/conv, inner_y/conv), inner_w/conv, inner_h/conv,
                        lw=1, edgecolor='blue', facecolor=color, alpha=0.7
                    ))
                
                ax.set_xlim(-5/conv, (final_plano_w + 5)/conv)
                ax.set_ylim(-5/conv, (final_plano_h + 5)/conv)
                ax.set_title(f"Plano Layout: {pcs_per_plano} pcs on {final_plano_w/conv:.2f}×{final_plano_h/conv:.2f} {unit} sheet", fontsize=14, fontweight='bold')
                ax.set_xlabel(f"Width ({unit})")
                ax.set_ylabel(f"Height ({unit})")
                
                st.pyplot(fig)
                st.info(f"💡 Blue = Normal | Orange = Rotated 90°")
    
    # PATTERN 2D
    st.markdown("---")
    with st.expander("📐 2D Technical Pattern", expanded=False):
        if st.button("🎨 Generate Pattern", key="gen_pattern"):
            with st.spinner("Generating pattern..."):
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
                
                fig, ax = plt.subplots(figsize=(12, 8))
                
                for val_x in x:
                    ax.plot([val_x/conv, val_x/conv], [y_bottom/conv, y_actual_top/conv], color='black', lw=1)
                
                ax.plot([x[0]/conv, x[-1]/conv], [y_actual_top/conv, y_actual_top/conv], color='black', lw=1.5)
                ax.plot([x[0]/conv, x[-1]/conv], [y_top_fold/conv, y_top_fold/conv], color='black', ls='--', lw=1.2, label='Fold line')
                ax.plot([x[0]/conv, x[-1]/conv], [y_bottom/conv, y_bottom/conv], color='black', lw=1.5)
                ax.plot([x[0]/conv, x[-1]/conv], [y_green/conv, y_green/conv], color='green', ls='--', lw=1, label='Gusset')
                
                ax.plot([v_mids[0]/conv, v_mids[0]/conv], [y_green/conv, y_actual_top/conv], color='blue', lw=1.5)
                ax.plot([v_mids[1]/conv, v_mids[1]/conv], [y_green/conv, y_actual_top/conv], color='blue', lw=1.5)

                plt.plot([x[0], x[-1]], [y_base, y_base], color='blue', ls=':', alpha=0.5) 
                
                hole_size = 0.35
                for p_start, p_end in p_panels:
                    h1_x = p_start + (0.25 * P)
                    h2_x = p_start + (0.75 * P)
                    for h_x in [h1_x, h2_x]:
                        up_circ = plt.Circle((h_x/conv, y_hole_upper/conv), hole_size, color='blue', fill=False, lw=1.5)
                        low_circ = plt.Circle((h_x/conv, y_hole_lower/conv), hole_size, color='blue', fill=False, lw=1.5)
                        ax.add_patch(up_circ)
                        ax.add_patch(low_circ)
                
                p_mid1 = (x[2] + x[3]) / 2
                p_mid2 = (x[4] + x[5]) / 2
                
                ax.plot([v_mids[0]/conv, x[0]/conv], [y_green/conv, (y_green - (v_mids[0] - x[0]))/conv], color='red', lw=2)
                ax.plot([v_mids[0]/conv, p_mid1/conv], [y_green/conv, y_bottom/conv], color='red', lw=2)
                ax.plot([p_mid1/conv, v_mids[1]/conv], [y_bottom/conv, y_green/conv], color='red', lw=2)
                ax.plot([v_mids[1]/conv, p_mid2/conv], [y_green/conv, y_bottom/conv], color='red', lw=2)
                ax.plot([p_mid2/conv, x[5]/conv], [y_bottom/conv, y_base/conv], color='red', lw=2)
                
                ax.set_aspect('equal')
                ax.set_title(f"Paper Bag Pattern: {P/conv:.2f}×{L/conv:.2f}×{T/conv:.2f} {unit}", fontsize=14, fontweight='bold')
                ax.set_xlabel(f"Width ({unit})")
                ax.set_ylabel(f"Height ({unit})")
                ax.grid(True, which='both', linestyle=':', alpha=0.3)
                ax.legend()
                
                st.pyplot(fig)

# ==========================================
# TAB 2: CUSTOMER PREVIEW RESULTS
# ==========================================
# Melanjutkan output untuk Tab Customer (hasil harga & mockup)
with tab2:
    st.markdown("---")
    st.header("💰 Quote & Preview")
    
    if unit_price > 0:
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric("Price per Piece", f"$ {unit_price:,.0f}", help="Based on your quantity")
        with col_res2:
            st.metric("Total Price", f"$ {total_selling_price:,.0f}")
    else:
        st.warning("Please configure production settings in Seller Tab to see prices.")

    st.markdown("---")
    
    # 3D Mockup
    st.subheader("🎨 3D Preview")
    
    col1, col2 = st.columns(2)
    bag_color = col1.color_picker("Bag Color", "#D3D3D3")
    handle_color = col2.color_picker("Handle Color", "#222222")
    
    if st.button("🎨 Generate Preview", type="primary"):
        with st.spinner("Rendering 3D mockup..."):
            fig = generate_3d_mockup(P, L, T, bag_color, handle_color, conv, unit)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.button("💵 Request Quote", type="primary", disabled=True, help="Feature available when embedded on your website")

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Paper Bag Calculator Pro</strong> v1.0 | Built with Streamlit</p>
    <p>For business inquiries: <a href='mailto:chaharudin202@gmail.com'>chaharudin202@gmail.com</a></p>
</div>
""", unsafe_allow_html=True) 
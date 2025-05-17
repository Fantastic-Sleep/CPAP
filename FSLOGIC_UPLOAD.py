import streamlit as st
import pandas as pd
from datetime import date
import io, os, calendar
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, Image)
from reportlab.lib import colors
from reportlab.lib.colors import Color
lavender = Color(184/255, 148/255, 245/255) 
from reportlab.lib.colors import purple, white,black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ---------- Streamlit page ----------
st.set_page_config(page_title="CPAP EOB Calculator", layout="wide")

# ---------- Sidebar ----------
st.sidebar.title("Insurance Parameters")
eff_date        = st.sidebar.date_input("Insurance Effective Date", value=date(2024, 1, 1))
deductible_total= st.sidebar.number_input("Deductible Total", 0.0, value=0.0, step=1.0)
deductible_met  = st.sidebar.number_input("Deductible Already Met", 0.0, value=0.0, step=1.0)
oop_max         = st.sidebar.number_input("OOP Max", 0.0, value=4000.0, step=1.0)
oop_met         = st.sidebar.number_input("OOP Already Met", 0.0, value=0.0, step=1.0)
coinsurance_rate= st.sidebar.number_input("Coinsurance %", 0.0, 100.0, 20.0, step=1.0) / 100
reset_date      = st.sidebar.date_input("Deductible Resets On", value=date(2026, 1, 1))

# ---------- Fee schedule (updated defaults) ----------
fee_schedule = [
    # one‑time supplies
    {"code": "A7030", "charge": 142.03, "type": "one-time", "desc": "Full Face Mask"},
    {"code": "A7031", "charge": 53.03,  "type": "one-time", "desc": "Full Face Cushion"},
    {"code": "A7035", "charge": 27.22,  "type": "one-time", "desc": "HEADGEAR"},
    {"code": "A7036", "charge": 7.80,   "type": "one-time", "desc": "CHINSTRAP"},
    {"code": "A4604", "charge": 31.87,  "type": "one-time", "desc": "HEATED TUBING"},
    {"code": "A0738", "charge": 7.38,   "type": "one-time", "desc": "CPAP FILTER (2 Included)"},
    # monthly rentals (10‑month capped)
    {"code": "E0601", "charge": 73.18, "type": "monthly", "months": 10, "desc": "CPAP Device Rental"},
    {"code": "E0562", "charge": 22.38, "type": "monthly", "months": 10, "desc": "Humidifier Rental"},
]

# ---------- Helper ----------
def apply_cost_share(amount, ded_rem, oop_rem):
    patient = insurance = 0.0
    if ded_rem > 0:
        d = min(amount, ded_rem)
        patient += d; ded_rem -= d; amount -= d
    if amount > 0:
        if oop_rem > 0:
            coins_pat = min(amount * coinsurance_rate, oop_rem)
            patient += coins_pat
            insurance = amount - coins_pat
            oop_rem -= coins_pat
        else:
            insurance = amount
    return round(patient,2), round(insurance,2), ded_rem, oop_rem

# ---------- Build input rows ----------
setup_rows=[]
for item in fee_schedule:
    default_desc = item["desc"] if item["type"]=="one-time" else f"{item['desc']} (1st Month)"
    setup_rows.append({"Code": item["code"], "Description": default_desc, "Price": round(item["charge"],2)})
df_setup_orig=pd.DataFrame(setup_rows)

col1,col2=st.columns([3,1], gap="large")
with col1:
    with st.expander("🛠️ Setup Charges (Click to Expand)", expanded=False):
        st.header("Setup Charges Breakdown")
        df_setup = pd.DataFrame(columns=["Code","Description","Price"])
        # convert each row to three inputs
        for idx,row in df_setup_orig.iterrows():
            c1,c2,c3 = st.columns([1,3,1])
            if row["Code"] == "A7030":
                code_options = ["A7030", "A7034"]
                desc_map = {
                    "A7030": "Full Face Mask (1-time)",
                    "A7034": "Nasal Mask (1-time)"
                }
                price_map = {
                    "A7030": 142.03,
                    "A7034": 88.66
                }
                code = c1.selectbox("Code", code_options, index=0, key=f"code_{idx}")           
                desc = c2.text_input("Description", desc_map[code], key=f"desc_{idx}")            
                price= c3.number_input("Price ($)", price_map[code], step=0.01, key=f"price_{idx}")
            elif row["Code"] == "A7031":
                code_options = ["A7031", "A7032", "A7033"]
                desc_map = {
                    "A7031": "Full Face Cushion (1-time)",
                    "A7032": "Nasal Cushion (1-time)",
                    "A7033": "Nasal Pillow Cushion (1-time)"
                }
                price_map = {
                    "A7031": 53.03,
                    "A7032": 30.40,
                    "A7033": 22.53,
                }
                code = c1.selectbox("Code", code_options, index=0, key=f"code_{idx}")           
                desc = c2.text_input("Description", desc_map[code], key=f"desc_{idx}")            
                price= c3.number_input("Price ($)", price_map[code], step=0.01, key=f"price_{idx}")

            elif row["Code"] == "A4604":
                code_options = ["A4604", "A7037"]
                desc_map = {
                    "A4604": "HEATED TUBING (1-time)",
                    "A7037": "TUBING (1-time)",
                   
                }
                price_map = {
                    "A4604": 31.87,
                    "A7037": 25.52,
                   
                }
                code = c1.selectbox("Code", code_options, index=0, key=f"code_{idx}")           
                desc = c2.text_input("Description", desc_map[code], key=f"desc_{idx}")            
                price= c3.number_input("Price ($)", price_map[code], step=0.01, key=f"price_{idx}")
            elif row["Code"] == "E0601":
                code_options = ["E0601", "E0470"]
                desc_map = {
                    "E0601": "CPAP Device Rental (1st Month)",
                    "E0470": "BiPAP (1-time)",
                   
                }
                price_map = {
                    "E0601": 73.18,
                    "E0470": 185.52,
                   
                }
                code = c1.selectbox("Code", code_options, index=0, key=f"code_{idx}")           
                desc = c2.text_input("Description", desc_map[code], key=f"desc_{idx}")            
                price= c3.number_input("Price ($)", price_map[code], step=0.01, key=f"price_{idx}")
            else:
                code = c1.text_input("Code", row["Code"], key=f"code_{idx}")
                desc = c2.text_input("Description", row["Description"], key=f"desc_{idx}")
                price= c3.number_input("Price ($)", value=row["Price"], step=0.01, key=f"price_{idx}")
            df_setup.loc[idx] = [code, desc, price]
    st.markdown(f"**Setup Total:** ${df_setup['Price'].sum():.2f}")
    

# ---------- Cost‑share for Table 1 ----------
ded_rem = max(deductible_total - deductible_met,0.0)
oop_rem = max(oop_max - oop_met,0.0)
setupprice = 0 
setup_breakdown=[]
first_month_patient=first_month_insurance=0.0
for _, r in df_setup.iterrows():
    pat, ins, ded_rem, oop_rem = apply_cost_share(r["Price"], ded_rem, oop_rem)
    
    setup_breakdown.append({"Code":r["Code"],"Description":r["Description"],
                            "Allowed":r["Price"],"Patient Pays":pat,"Insurance Pays":ins})
    if "(1st Month)" in r["Description"]:
        first_month_patient  += pat
        
        first_month_insurance+= ins
        
df_share = pd.DataFrame(setup_breakdown)

with col1:
    st.header("Cost‑share (Table 1 results)")
    st.dataframe(df_share, hide_index=True, use_container_width=True)

# ---------- Monthly schedule ----------
monthly_charge = sum(i["charge"] for i in fee_schedule if i["type"]=="monthly")
max_months     = max(i["months"]  for i in fee_schedule if i["type"]=="monthly")
schedule=[{"Month":calendar.month_name[eff_date.month],
           "Patient Pays":round(first_month_patient,2),
           "Insurance Pays":round(first_month_insurance,2)}]
year_ded_rem, year_oop_rem = ded_rem, oop_rem
for m in range(2,max_months+1):
    idx=(eff_date.month+m-2)%12+1
    if idx==reset_date.month:
        year_ded_rem = deductible_total
        year_oop_rem = oop_max
    pat,ins,year_ded_rem,year_oop_rem = apply_cost_share(monthly_charge, year_ded_rem, year_oop_rem)
    schedule.append({"Month":calendar.month_name[idx],"Patient Pays":pat,"Insurance Pays":ins})
df_schedule = pd.DataFrame(schedule)

with col1:
    st.header("Monthly Rental Schedule (Months 1‑10)")
    st.dataframe(df_schedule, hide_index=True, use_container_width=True)

# ---------- Totals ----------
total_patient   = df_share["Patient Pays"].sum() + df_schedule["Patient Pays"].iloc[1:].sum()
total_insurance = df_share["Insurance Pays"].sum() + df_schedule["Insurance Pays"].iloc[1:].sum()
supply_total    = df_setup["Price"].sum() - monthly_charge  # one‑time supplies total
total_upfront   = supply_total + monthly_charge*max_months

with col2:
    st.header("Estimated Totals")
    st.markdown(f"- **Total Paid by Patient:** ${total_patient:.2f}")
    st.markdown(f"- **Total Paid by Insurance:** ${total_insurance:.2f}")
    st.markdown(f"- **Total if Patient Pays All Upfront:** ${total_upfront:.2f}")
    st.markdown(f"- **Grand Total (Combined):** ${total_upfront:.2f}")

# ---------- PDF generation ----------
styles = getSampleStyleSheet()
heading_style = ParagraphStyle(
    'full_width_heading',
    parent=styles['Normal'],
    fontSize=10,
    textColor=white,
    backColor=lavender,
    leading=12,
    alignment=0,  # center align
    spaceAfter=6,
    spaceBefore=6,
    leftIndent=4,
    rightIndent=0,
    borderPadding=4,
)

if col2.button("Generate PDF Report"):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=letter,
                          leftMargin=20,rightMargin=20,topMargin=10,bottomMargin=10)
    styles=getSampleStyleSheet()
    body=ParagraphStyle('body',parent=styles['BodyText'],fontSize=8,leading=10)
    tbl_style = TableStyle([
    ('GRID', (0, 0), (-1, -1), 0.5, black),
    ('BACKGROUND', (0, 0), (-1, 0), lavender),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    
    ])
    el=[]
    logo_filename = "SFlogo.PNG"
    # either relative to this script:
        
    logo_path = os.path.join(os.path.dirname(__file__), logo_filename)
        # or simpler, relative to the app’s cwd:
        # logo_path = os.path.join(os.getcwd(), logo_filename)

    st.write("Logo path:", logo_path, "Exists?", os.path.isfile(logo_path))

    if os.path.isfile(logo_path):
        with open(logo_path, "rb") as f:
            el.append(Image(io.BytesIO(f.read()), width=420, height=60))
    else:
        st.error(f"⚠️ Could not find {logo_filename} at {logo_path}")
##    logo=os.path.join(os.path.dirname(__file__),"SFlogo.png")
##    if os.path.isfile(logo):
##        with open(logo,"rb") as f:
##            el.append(Image(io.BytesIO(f.read()),width=420,height=60))
    el.append(Spacer(1,6))
    el.append(Paragraph(f"Patient Name: _______________________   DOB: __________      Date: {date.today():%m/%d/%Y}",styles['Heading4']))
    el.append(Spacer(1,6))
    el.append(Paragraph("1) Total Due Now (Supplies + First Month)", heading_style))
    data1=[["CPT","Description","Allowed","Patient","Insurance"]]+[
        [r["Code"],r["Description"],f"${r['Allowed']:.2f}",f"${r['Patient Pays']:.2f}",f"${r['Insurance Pays']:.2f}"]
        for r in setup_breakdown]
    #data1.append(["Setup Total:", f"${df_setup['Price'].sum():.2f}"])
    data1.append(["", "Setup Total","", f"${df_share['Patient Pays'].sum():.2f}",""])
    t1=Table(data1,colWidths=[50,175,60,60,60],hAlign="LEFT");t1.setStyle(tbl_style)
    
    
    
    el+=[t1,Spacer(1,6)]
   
    el.append(Paragraph("2) Monthly Rental Schedule", heading_style))
    data2=[["Month","Patient","Insurance"]]+[
        [r["Month"],f"${r['Patient Pays']:.2f}",f"${r['Insurance Pays']:.2f}"]
        for r in schedule]
    #t2=Table(data2,colWidths=[250, 160, 162],hAlign="LEFT");t2.setStyle(tbl_style)
    t2=Table(data2,colWidths=[160, 70, 70],hAlign="LEFT");t2.setStyle(tbl_style)
    el+=[t2,Spacer(1,6)]
    
    data3=[["Category","Total"],
           ["Patient Paid",f"${total_patient:.2f}"],
           ["Insurance Paid",f"${total_insurance:.2f}"]]
    t3=Table(data3,colWidths=[180,100],hAlign="LEFT");t3.setStyle(tbl_style)
    el+=[Paragraph("3) Estimated Totals",  heading_style), t3, Spacer(1,4)]
    data4=[["If patient pays everything upfront:",f"${total_patient:.2f}"]]
    t4=Table(data4,colWidths=[180,100],hAlign="LEFT");#t4.setStyle(tbl_style)
    el+=[Paragraph("4) Optional Full Prepay Amount", heading_style), t4, Spacer(1,4)]
    data5=[["Description","Total"],["Combined Cost",f"${total_upfront:.2f}"]]
    t5=Table(data5,colWidths=[180,100],hAlign="LEFT");t5.setStyle(tbl_style)
    el+=[Paragraph("5) Overall Cost Summary", heading_style), t5, Spacer(1,6)]
    el.append(Paragraph("Please select one:   [ ] Monthly Rental Option     [ ] Lump Sum Payment",
                        ParagraphStyle('footer',fontSize=8)))
    el.append(Spacer(1,6))
    el.append(Paragraph("Patient Signature: __________________________   Date: __________________",
                        ParagraphStyle('footer',fontSize=8)))
    doc.build(el)
    buf.seek(0)
    col2.markdown('<span style="color:green; font-weight:bold; font-size:16px;">✅ PDF Generated Successfully</span>', unsafe_allow_html=True)
    el.append(Spacer(1,10))
    col2.download_button("Download PDF", buf, "cpap_eob.pdf", "application/pdf")

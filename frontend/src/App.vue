<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, setCsrf } from './api'

type Row = Record<string, any>
const BULAN = ['JANUARI','FEBRUARI','MARET','APRIL','MEI','JUNI','JULI','AGUSTUS','SEPTEMBER','OKTOBER','NOVEMBER','DESEMBER']
const HARI = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu']
const router = useRouter(); const route = useRoute()
const loading = ref(false); const saving = ref(false); const configured = ref(false); const authenticated = ref(false); const user = ref('')
const authMode = computed(() => configured.value ? 'login' : 'setup')
const credentials = reactive({ username:'admin', password:'' })
const collapsed = ref(false); const dark = ref(localStorage.getItem('theme') !== 'light'); const mobileNav = ref(false)
const data = ref<Row[]>([]); const periods = ref<Row[]>([]); const employees = ref<Row[]>([]); const selectedPeriod = ref<number|undefined>(); const summary = reactive<Row>({})
const employeeDialog = ref(false); const editingEmployee = ref(''); const periodDialog = ref(false); const attendanceRows = ref<Row[]>([]); const weeks = ref<Row[]>([])
const attendance = reactive({ id_minggu: undefined as number|undefined, tanggal:'' }); const attendanceDays = ref<string[]>([])
const employee = reactive<Row>({ id_karyawan:'', nama:'', ptkp:'', tipe_gaji:'harian', kode_bagian:'', jabatan:'', tgl_awal_kerja:'', tgl_akhir_kerja:'', policy_code:'', upah_harian:0, gaji_bulanan:0, uang_makan_hari:0, status_aktif:1, catatan:'' })
const now = new Date()
const newPeriod = reactive({ bulan: now.getMonth()+1, tahun: now.getFullYear() })
const transferForm = reactive<Row>({ no_referensi:'', tanggal:'', nominal:0, bank:'', keterangan:'' })
const simpleForm = reactive<Row>({ id_karyawan:'', nama:'', tanggal:'', nominal:0, keterangan:'' })
const reportType = ref('internal')

const menu = [
 {key:'dashboard',path:'/',label:'Dashboard',icon:'DataAnalysis'}, {key:'karyawan',path:'/karyawan',label:'Karyawan',icon:'User'}, {key:'bagian',path:'/bagian',label:'Bagian',icon:'OfficeBuilding'}, {key:'aturan',path:'/aturan',label:'Aturan Payroll',icon:'Setting'},
 {key:'periode',path:'/periode',label:'Periode Payroll',icon:'Calendar'}, {key:'kehadiran',path:'/kehadiran',label:'Kehadiran',icon:'EditPen'},
 {key:'rekap',path:'/rekap',label:'Rekap Gaji',icon:'TrendCharts'}, {key:'transfer',path:'/transfer',label:'Transfer',icon:'CreditCard'},
 {key:'potongan',path:'/potongan',label:'Potongan',icon:'Remove'}, {key:'kasbon',path:'/kasbon',label:'Kasbon',icon:'Wallet'},
 {key:'thr',path:'/thr',label:'THR',icon:'Present'}, {key:'slip',path:'/slip',label:'Slip Gaji',icon:'Tickets'}, {key:'laporan',path:'/laporan',label:'Laporan',icon:'Document'},
 {key:'backup',path:'/backup',label:'Backup & Restore',icon:'FolderOpened'}, {key:'log',path:'/audit-log',label:'Audit Log',icon:'List'}
]
const active = computed(() => String(route.name || 'dashboard'))
const current = computed(() => menu.find(x=>x.key===active.value) || menu[0])
const needsPeriod = computed(()=>['kehadiran','rekap','transfer','potongan','thr','slip','laporan'].includes(active.value))
const currentPeriod = computed(()=>periods.value.find(p=>p.id_periode===selectedPeriod.value))
const columns = computed(() => {
 const first = data.value[0] || {}; const priority=['id_karyawan','nama','tipe_gaji','nama_periode','tgl_mulai','status','nominal','total_bersih','selisih','aksi','tabel','waktu']
 return [...priority.filter(k=>k in first), ...Object.keys(first).filter(k=>!priority.includes(k) && !k.startsWith('id_'))]
})
const formatLabel=(key:string)=>key.replace(/_/g,' ').replace(/\b\w/g,(c:string)=>c.toUpperCase())
const rupiah=(v:any)=>typeof v==='number' ? new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(v) : (v ?? '—')
function summaryMethod({columns:cols,data}:any){
 if(!data.length) return cols.map(()=> '')
 return cols.map((col:any,i:number)=>{
  if(i===0) return 'TOTAL'
  const key=col.property
  if(!key) return ''
  const total=data.reduce((sum:number,row:Row)=>sum+(typeof row[key]==='number'?row[key]:0),0)
  return typeof (data[0]&&data[0][key])==='number' ? rupiah(total) : ''
 })
}
const printPage=()=>window.print()
async function withSaving(job:()=>Promise<any>){ if(saving.value)return; saving.value=true; try{ await job() } finally { saving.value=false } }

watch(dark, value => { document.documentElement.classList.toggle('dark',value); localStorage.setItem('theme', value?'dark':'light') }, {immediate:true})
watch(()=>route.path,()=>{ mobileNav.value=false; if(authenticated.value) loadPage() })
watch(selectedPeriod,()=>{ if(authenticated.value && needsPeriod.value) loadPage() })

async function boot(){
 try { const s=await api<any>('/api/auth/status'); configured.value=s.configured; authenticated.value=s.authenticated; user.value=s.user||''; if(authenticated.value) await loadPeriodsAndPage() }
 catch(e:any){ ElMessage.error(e.message) }
}
async function submitAuth(){
 loading.value=true
 try { const path=authMode.value==='setup'?'/api/auth/setup':'/api/auth/login'; const result=await api<any>(path,{method:'POST',body:JSON.stringify(credentials)}); setCsrf(result.csrf); configured.value=true; authenticated.value=true; user.value=result.user; credentials.password=''; await loadPeriodsAndPage(); ElMessage.success(authMode.value==='setup'?'Administrator berhasil dibuat.':'Selamat datang kembali.') }
 catch(e:any){ ElMessage.error(e.message) } finally { loading.value=false }
}
async function logout(){ try{await api('/api/auth/logout',{method:'POST'});}finally{authenticated.value=false;user.value='';sessionStorage.clear()} }
async function loadPeriodsAndPage(){ periods.value=await api<Row[]>('/api/periode'); if(!selectedPeriod.value&&periods.value.length) selectedPeriod.value=periods.value[0].id_periode; await loadPage() }
async function loadPage(){
 loading.value=true; data.value=[]
 try {
  if(['potongan','kasbon'].includes(active.value)&&!employees.value.length) employees.value=await api('/api/karyawan?aktif=0')
  if(active.value==='dashboard') Object.assign(summary,await api('/api/dashboard'))
  else if(active.value==='karyawan') data.value=await api('/api/karyawan?aktif=0')
  else if(active.value==='periode') data.value=periods.value=await api('/api/periode')
  else if(active.value==='bagian') data.value=await api('/api/bagian')
  else if(active.value==='aturan') data.value=await api('/api/aturan')
  else if(active.value==='kasbon') data.value=await api('/api/kasbon')
  else if(active.value==='backup') data.value=await api('/api/backup')
  else if(active.value==='log') data.value=await api('/api/log?limit=200')
  else if(selectedPeriod.value){
   const id=selectedPeriod.value
   if(active.value==='kehadiran'){ const detail=await api<any>(`/api/periode/${id}`); weeks.value=detail.minggu||[]; if(!weeks.value.some(w=>w.id_minggu===attendance.id_minggu)){ attendance.id_minggu=weeks.value.length?weeks.value[0].id_minggu:undefined; attendance.tanggal=''; attendanceRows.value=[] } await muatHari() }
   else if(active.value==='rekap'){ const r=await api<any>(`/api/rekap/${id}`); data.value=r.baris||[]; Object.assign(summary,r.total||{}) }
   else if(active.value==='transfer'){ const r=await api<any>(`/api/transfer/${id}`); data.value=r.daftar||[]; Object.assign(summary,{total_transfer:r.total||0,target_netto:r.target_netto||0,selisih_transfer:r.selisih||0}) }
   else if(active.value==='potongan') data.value=await api(`/api/potongan/${id}`)
   else if(active.value==='thr'){ const map=await api<Row>(`/api/thr/${id}`); data.value=Object.values(map||{}) }
   else if(active.value==='slip'){ const r=await api<any>(`/api/rekap/${id}`); data.value=r.baris||[] }
   else if(active.value==='laporan'){ const r=await api<any>(`/api/laporan/${id}?jenis=${reportType.value}`); data.value=r.baris||[]; Object.assign(summary,r.total||{}) }
  }
 } catch(e:any){ if(e.status===401){authenticated.value=false}else ElMessage.error(e.message) } finally { loading.value=false }
}
function resetEmployee(){editingEmployee.value='';Object.assign(employee,{id_karyawan:'',nama:'',ptkp:'',tipe_gaji:'harian',kode_bagian:'',jabatan:'',tgl_awal_kerja:'',tgl_akhir_kerja:'',policy_code:'',upah_harian:0,gaji_bulanan:0,uang_makan_hari:0,status_aktif:1,catatan:''})}
function editEmployee(row:Row){editingEmployee.value=row.id_karyawan;Object.assign(employee,row);employeeDialog.value=true}
async function saveEmployee(){ try{const path=editingEmployee.value?`/api/karyawan/${editingEmployee.value}`:'/api/karyawan';await api(path,{method:editingEmployee.value?'PUT':'POST',body:JSON.stringify(employee)}); employeeDialog.value=false; resetEmployee(); await loadPage(); ElMessage.success('Karyawan disimpan.')}catch(e:any){ElMessage.error(e.message)} }
async function savePeriod(){
 const nama=`${BULAN[newPeriod.bulan-1]} ${newPeriod.tahun}`
 if(periods.value.some(p=>String(p.nama||'').toUpperCase()===nama)){ElMessage.warning(`Periode ${nama} sudah ada. Pilih bulan atau tahun lain.`);return}
 try{
  const tgl_mulai=`${newPeriod.tahun}-${String(newPeriod.bulan).padStart(2,'0')}-01`
  await api('/api/periode',{method:'POST',body:JSON.stringify({nama,tgl_mulai})})
  periodDialog.value=false
  await loadPeriodsAndPage()
  ElMessage.success(`Periode ${nama} dibuat.`)
 }catch(e:any){ElMessage.error(e.message)}
}
async function togglePeriod(){if(!selectedPeriod.value||!currentPeriod.value)return;const next=currentPeriod.value.status==='draft'?'tutup':'draft';try{if(next==='tutup')await ElMessageBox.confirm('Setelah ditutup, input payroll periode ini akan dikunci.','Tutup Periode',{type:'warning'});await api(`/api/periode/${selectedPeriod.value}/status`,{method:'POST',body:JSON.stringify({status:next})});await loadPeriodsAndPage();ElMessage.success(next==='tutup'?'Periode ditutup.':'Periode dibuka kembali.')}catch(e:any){if(e!=='cancel')ElMessage.error(e.message||'Perubahan dibatalkan.')}}
async function deleteEmployee(row:Row){ try{await ElMessageBox.confirm(`Nonaktifkan ${row.nama}?`,'Konfirmasi',{type:'warning'});await api(`/api/karyawan/${row.id_karyawan}`,{method:'DELETE'});await loadPage()}catch{} }
async function loadAttendance(){ if(!attendance.id_minggu||!attendance.tanggal)return; try{attendanceRows.value=await api(`/api/kehadiran?id_minggu=${attendance.id_minggu}&tanggal=${attendance.tanggal}`)}catch(e:any){ElMessage.error(e.message)} }
function namaHari(iso:string){ return HARI[new Date(`${iso}T00:00:00`).getDay()] }
const labelBulan=(b:string)=>b.charAt(0)+b.slice(1).toLowerCase()
function labelHari(iso:string){ return `${namaHari(iso)}, ${iso.slice(8,10)}/${iso.slice(5,7)}` }
async function muatHari(){ attendanceDays.value = attendance.id_minggu ? await api<string[]>(`/api/minggu/${attendance.id_minggu}/hari`) : [] }
async function pilihMinggu(){ attendance.tanggal=''; attendanceRows.value=[]; try{ await muatHari() }catch(e:any){ ElMessage.error(e.message) } }
async function pilihHari(iso:string){ attendance.tanggal=iso; await loadAttendance() }
function hadirkanSemua(){ if(!attendanceRows.value.length)return; attendanceRows.value.forEach(r=>{ r.upah_hari=1 }); ElMessage.success('Semua karyawan ditandai hadir. Klik Simpan Kehadiran untuk menyimpan.') }
function toggleHadir(row:Row){ row.upah_hari = row.upah_hari ? 0 : 1 }
async function saveAttendance(){ try{await api('/api/kehadiran/batch',{method:'POST',body:JSON.stringify({...attendance,baris:attendanceRows.value})});ElMessage.success('Kehadiran tersimpan.')}catch(e:any){ElMessage.error(e.message)} }
async function createTransfer(){ if(!selectedPeriod.value)return; try{await api(`/api/transfer/${selectedPeriod.value}`,{method:'POST',body:JSON.stringify(transferForm)});Object.assign(transferForm,{no_referensi:'',tanggal:'',nominal:0,bank:'',keterangan:''});await loadPage();ElMessage.success('Transfer ditambahkan.')}catch(e:any){ElMessage.error(e.message)} }
function escapeHtml(value:unknown){return String(value??'—').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]||ch))}
async function printSlip(row:Row){
 if(!selectedPeriod.value){ElMessage.warning('Pilih periode payroll terlebih dahulu.');return}
 try{
  const detail=await api<any>(`/api/slip/${selectedPeriod.value}/${encodeURIComponent(row.id_karyawan)}`)
  const h:Row=detail.hasil||{}
  const thrRow:any=h.thr
  const thrJumlah=thrRow&&typeof thrRow==='object'?Number(thrRow.jumlah||0):Number(thrRow||0)
  const potongan=Number(h.potongan||0)
  const totalPenghasilan=Number(h.total_penghasilan||0)
  const totalBersih=totalPenghasilan-potongan
  const line=(label:string,value:any,bold=false)=>`<tr${bold?' class="bold"':''}><th>${escapeHtml(label)}</th><td>${typeof value==='number'?rupiah(value):escapeHtml(value)}</td></tr>`
  const w=window.open('','_blank','width=760,height=900')
  if(!w)return ElMessage.error('Popup diblokir browser.')
  w.document.write(`<title>Slip ${escapeHtml(String(h.nama||row.nama||''))}</title><style>
   body{font:13px Manrope,Arial,sans-serif;padding:32px;color:#17213a}
   h1{font-size:18px;margin:0 0 2px}h2{font-size:12px;font-weight:600;color:#5a6b8c;margin:0 0 18px}
   table.meta{width:100%;border-collapse:collapse;margin-bottom:16px}
   table.meta td{padding:3px 6px;font-size:12px;color:#5a6b8c}
   table.meta td.val{color:#17213a;font-weight:600;padding-right:18px}
   h3{font-size:10px;letter-spacing:1px;color:#356df3;margin:0 0 6px;text-transform:uppercase}
   table.rows{width:100%;border-collapse:collapse;margin-bottom:14px}
   table.rows th,table.rows td{padding:7px 9px;border-bottom:1px solid #e5eaf2;text-align:left;font-size:12px}
   table.rows th{font-weight:500;color:#5a6b8c;width:62%}
   table.rows td{text-align:right;font-variant-numeric:tabular-nums}
   tr.bold th,tr.bold td{font-weight:800;color:#17213a;border-top:2px solid #17213a;border-bottom:0}
   .print-actions{margin-top:18px}
   @media print{.print-actions{display:none}}
  </style>
  <h1>PT. MEGA ARTHA MAKMUR</h1>
  <h2>Slip Gaji &amp; Upah · ${escapeHtml(String((detail.periode&&detail.periode.bulan)||currentPeriod.value?.nama||''))}</h2>
  <table class="meta">
   <tr><td>ID Karyawan</td><td class="val">${escapeHtml(String(h.id_karyawan||''))}</td><td>Hari Masuk</td><td class="val">${escapeHtml(String(h.hari_masuk||0))}</td></tr>
   <tr><td>Nama</td><td class="val">${escapeHtml(String(h.nama||''))}</td><td>Bagian</td><td class="val">${escapeHtml(String(h.kode_bagian||''))}</td></tr>
   <tr><td>Jabatan</td><td class="val">${escapeHtml(String(h.jabatan||''))}</td><td>Tipe Gaji</td><td class="val">${escapeHtml(String(h.tipe_gaji||''))}</td></tr>
  </table>
  <h3>Penghasilan</h3><table class="rows">
   ${line('Gaji Bulanan',Number(h.gaji_bulanan||0))}
   ${line('Upah Harian',Number(h.upah_harian||0))}
   ${line('Uang Makan',Number(h.uang_makan||0))}
   ${line('Tambahan Tanggal Merah',Number(h.tambahan_tgl_merah||0))}
   ${line('Uang Makan Lembur',Number(h.uang_makan_lembur||0))}
   ${line('Lembur Malam',Number(h.lembur_malam||0))}
   ${line('Lembur Jam',Number(h.lembur_jam||0))}
   ${line('Total Penghasilan',totalPenghasilan,true)}
  </table>
  <h3>Potongan</h3><table class="rows">${line('Total Potongan',potongan,true)}</table>
  <h3>Total Bersih</h3><table class="rows">${line('Total Bersih (Netto)',totalBersih,true)}</table>
  ${thrJumlah?`<h3>THR (Terpisah)</h3><table class="rows">${line('THR',thrJumlah,true)}</table>`:''}
  <p class="print-actions"><button id="print-slip">Cetak</button></p>`)
  w.document.close()
  w.document.getElementById('print-slip')?.addEventListener('click',()=>w.print())
 }catch(e:any){ElMessage.error(e.message)}
}
async function createSimple(kind:'potongan'|'kasbon'){ try{ const path=kind==='potongan'?`/api/potongan/${selectedPeriod.value}`:'/api/kasbon'; await api(path,{method:'POST',body:JSON.stringify(simpleForm)});Object.assign(simpleForm,{id_karyawan:'',nama:'',tanggal:'',nominal:0,keterangan:''});await loadPage();ElMessage.success('Data disimpan.')}catch(e:any){ElMessage.error(e.message)} }
async function allocateKasbon(row:Row){if(!selectedPeriod.value){ElMessage.warning('Pilih periode pada menu payroll terlebih dahulu.');return}try{const result=await ElMessageBox.prompt('Masukkan nominal cicilan untuk periode terpilih.','Alokasikan Kasbon',{inputType:'number',inputPattern:/^[1-9]\d*$/,inputErrorMessage:'Nominal harus lebih dari nol.'});await api('/api/kasbon/alokasi',{method:'POST',body:JSON.stringify({id_kasbon:row.id_kasbon,id_periode:selectedPeriod.value,jumlah:Number(result.value),keterangan:'Alokasi dari aplikasi'})});await loadPage();ElMessage.success('Cicilan kasbon dialokasikan.')}catch(e:any){if(e!=='cancel')ElMessage.error(e.message||'Alokasi dibatalkan.')}}
async function calculateThr(){if(!selectedPeriod.value)return;try{const map=await api<Row>(`/api/thr/${selectedPeriod.value}`,{method:'POST',body:'{}'});data.value=Object.values(map||{});ElMessage.success('THR dihitung terpisah dari payroll reguler.')}catch(e:any){ElMessage.error(e.message)}}
function downloadReport(){if(selectedPeriod.value)window.location.href=`/api/laporan/${selectedPeriod.value}/export?jenis=${reportType.value}`}
async function settleKasbon(row:Row){try{await ElMessageBox.confirm(`Tandai kasbon ${row.id_kasbon} sebagai lunas?`,'Konfirmasi',{type:'warning'});await api(`/api/kasbon/${row.id_kasbon}/lunasi`,{method:'POST',body:'{}'});await loadPage();ElMessage.success('Kasbon ditandai lunas.')}catch(e:any){if(e!=='cancel')ElMessage.error(e.message||'Operasi dibatalkan.')}}
async function deleteItem(kind:string,row:Row){try{await ElMessageBox.confirm('Data ini akan dihapus dari periode.','Konfirmasi',{type:'warning'});const path=kind==='transfer'?`/api/transfer/item/${row.id_transfer}`:`/api/potongan/item/${row.id_potongan}`;await api(path,{method:'DELETE'});await loadPage();ElMessage.success('Data dihapus.')}catch(e:any){if(e!=='cancel')ElMessage.error(e.message||'Operasi dibatalkan.')}}
async function createBackup(){try{await api('/api/backup',{method:'POST',body:'{}'});await loadPage();ElMessage.success('Backup berhasil dibuat.')}catch(e:any){ElMessage.error(e.message)}}
async function restoreBackup(row:Row){try{await ElMessageBox.confirm(`Restore ${row.nama}? Database saat ini akan diamankan otomatis.`,'Konfirmasi Restore',{type:'warning',confirmButtonText:'Restore'});await api('/api/backup/restore',{method:'POST',body:JSON.stringify({nama:row.nama})});await loadPeriodsAndPage();ElMessage.success('Database berhasil direstore.')}catch(e:any){if(e!=='cancel')ElMessage.error(e.message||'Restore dibatalkan.')}}
onMounted(boot)
</script>

<template>
 <div v-if="!authenticated" class="auth-page">
  <div class="auth-brand"><div class="brand-mark">MA</div><div><strong>MEGA ARTHA MAKMUR</strong><span>Sistem Rekap Gaji & Upah</span></div></div>
  <el-card class="auth-card" shadow="never">
   <div class="auth-kicker">AKSES LOKAL AMAN</div><h1>{{ authMode==='setup'?'Buat administrator':'Selamat datang' }}</h1>
   <p>{{ authMode==='setup'?'Siapkan akun pertama untuk aplikasi payroll lokal.':'Masuk untuk melanjutkan pengelolaan payroll.' }}</p>
   <el-form label-position="top" @submit.prevent="submitAuth">
    <el-form-item label="Nama pengguna"><el-input v-model="credentials.username" size="large" autocomplete="username" /></el-form-item>
    <el-form-item :label="authMode==='setup'?'Password (min. 10 karakter)':'Password'"><el-input v-model="credentials.password" type="password" show-password size="large" autocomplete="current-password" @keyup.enter="submitAuth" /></el-form-item>
    <el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submitAuth">{{ authMode==='setup'?'Buat Administrator':'Masuk ke Aplikasi' }}</el-button>
   </el-form><div class="local-note"><el-icon><Lock /></el-icon> Data tetap tersimpan di komputer ini</div>
  </el-card>
 </div>
 <div v-else class="app-shell">
  <aside class="sidebar" :class="{collapsed,open:mobileNav}">
   <div class="logo"><div class="brand-mark">MA</div><div class="logo-copy"><strong>Mega Artha</strong><span>Payroll System</span></div></div>
   <nav><button v-for="item in menu" :key="item.key" :class="{active:active===item.key}" @click="router.push(item.path)"><el-icon><component :is="item.icon" /></el-icon><span>{{item.label}}</span></button></nav>
   <div class="sidebar-foot"><span class="online-dot"></span><div><strong>Server lokal aktif</strong><small>127.0.0.1 · Non-Flask</small></div></div>
  </aside>
  <div class="main" :class="{wide:collapsed}">
   <header class="topbar"><div class="top-left"><el-button text circle class="mobile-menu" aria-label="Buka atau tutup menu navigasi" @click="mobileNav=!mobileNav"><el-icon><Menu /></el-icon></el-button><el-button text circle class="desktop-collapse" :aria-label="collapsed?'Lebarkan sidebar':'Ciutkan sidebar'" @click="collapsed=!collapsed"><el-icon><Fold v-if="!collapsed"/><Expand v-else/></el-icon></el-button><div class="breadcrumb">Operasional <span>/</span> <strong>{{current.label}}</strong></div></div><div class="top-actions"><el-button text circle :aria-label="dark?'Aktifkan tema terang':'Aktifkan tema gelap'" @click="dark=!dark"><el-icon><Moon v-if="!dark"/><Sunny v-else/></el-icon></el-button><div class="user-chip"><div class="avatar">{{user.slice(0,2).toUpperCase()}}</div><div><strong>{{user}}</strong><small>Administrator</small></div></div><el-button text circle aria-label="Keluar dari aplikasi" @click="logout"><el-icon><SwitchButton/></el-icon></el-button></div></header>
   <main class="content">
    <section class="page-head"><div><div class="eyebrow">PAYROLL WORKSPACE</div><h1>{{current.label}}</h1><p>Kelola data payroll secara lokal, konsisten, dan terkontrol.</p></div><div class="head-actions"><el-button v-if="active==='karyawan'" type="primary" @click="resetEmployee();employeeDialog=true"><el-icon><Plus/></el-icon>Tambah Karyawan</el-button><el-button v-if="active==='periode'" type="primary" @click="periodDialog=true"><el-icon><Plus/></el-icon>Buat Periode</el-button><el-button v-if="active==='backup'" type="primary" :loading="saving" @click="withSaving(createBackup)"><el-icon><Download/></el-icon>Buat Backup</el-button><el-button v-if="active==='laporan'" type="primary" @click="downloadReport"><el-icon><Download/></el-icon>Export Excel</el-button></div></section>
    <div v-if="needsPeriod" class="period-bar"><div><span>KONTEKS PERIODE</span><strong>Pilih periode payroll yang akan dikelola</strong></div><div class="period-controls"><el-tag v-if="currentPeriod" :type="currentPeriod.status==='draft'?'warning':'success'" effect="dark">{{currentPeriod.status==='draft'?'DRAFT':'DITUTUP'}}</el-tag><el-select v-model="selectedPeriod" placeholder="Pilih periode" size="large"><el-option v-for="p in periods" :key="p.id_periode" :label="p.nama" :value="p.id_periode"/></el-select><el-button v-if="currentPeriod" plain @click="togglePeriod">{{currentPeriod.status==='draft'?'Tutup':'Buka'}}</el-button></div></div>

    <template v-if="active==='dashboard'">
     <div class="metrics"><article><div class="metric-icon blue"><el-icon><User/></el-icon></div><div><span>Karyawan Aktif</span><strong>{{summary.karyawan_aktif??0}}</strong><small>Roster payroll saat ini</small></div></article><article><div class="metric-icon cyan"><el-icon><Clock/></el-icon></div><div><span>Tenaga Harian</span><strong>{{summary.harian??0}}</strong><small>Berbasis kehadiran</small></div></article><article><div class="metric-icon violet"><el-icon><Briefcase/></el-icon></div><div><span>Tenaga Bulanan</span><strong>{{summary.bulanan??0}}</strong><small>Gaji tetap bulanan</small></div></article><article><div class="metric-icon green"><el-icon><Calendar/></el-icon></div><div><span>Total Periode</span><strong>{{summary.periode??0}}</strong><small>Riwayat tersimpan</small></div></article></div>
     <div class="dashboard-grid"><el-card shadow="never" class="panel hero-panel"><div class="panel-title"><div><span>PERIODE TERKINI</span><h2>{{summary.periode_terakhir?.nama||'Belum ada periode'}}</h2></div><el-tag type="info" effect="plain">Lokal</el-tag></div><div class="hero-art"><div class="bars"><i v-for="h in [42,67,51,86,62,92,74]" :style="{height:h+'%'}"></i></div><div class="hero-copy"><strong>Siap untuk workflow payroll</strong><p>Buat periode, isi kehadiran, lalu tinjau rekap sebelum transfer.</p><el-button type="primary" plain @click="router.push('/periode')">Kelola Periode</el-button></div></div></el-card><el-card shadow="never" class="panel quick-panel"><div class="panel-title"><div><span>AKSES CEPAT</span><h2>Operasional</h2></div></div><button v-for="item in menu.slice(1,6)" @click="router.push(item.path)"><el-icon><component :is="item.icon"/></el-icon><span>{{item.label}}</span><el-icon><ArrowRight/></el-icon></button></el-card></div>
    </template>

    <template v-else-if="active==='kehadiran'">
     <el-card shadow="never" class="panel">
      <div v-if="currentPeriod" class="period-hint">Periode <strong>{{currentPeriod.nama}}</strong> · {{currentPeriod.tgl_mulai}} s/d {{currentPeriod.tgl_selesai}}</div>
      <div class="form-grid attendance-filter"><el-form-item label="Minggu ke-"><el-select v-model="attendance.id_minggu" @change="pilihMinggu"><el-option v-for="w in weeks" :key="w.id_minggu" :label="`Minggu ${w.minggu_ke} · ${w.tgl_mulai} — ${w.tgl_selesai}`" :value="w.id_minggu"/></el-select></el-form-item></div>
      <div class="day-picker-label">Pilih hari</div>
      <div class="day-picker"><button v-for="d in attendanceDays" :key="d" type="button" :class="{active:attendance.tanggal===d}" @click="pilihHari(d)">{{labelHari(d)}}</button><span v-if="!attendanceDays.length" class="day-empty">Pilih minggu terlebih dahulu.</span></div>
      <div class="form-actions"><el-button :disabled="!attendanceRows.length" @click="hadirkanSemua"><el-icon><Check/></el-icon>Hadirkan Semua</el-button><el-button type="primary" :disabled="!attendanceRows.length" :loading="saving" @click="withSaving(saveAttendance)">Simpan Kehadiran</el-button></div>
     </el-card>
     <el-card v-if="attendanceRows.length" shadow="never" class="panel table-panel"><div class="table-toolbar"><div><span>KEHADIRAN</span><strong>{{labelHari(attendance.tanggal)}} · {{attendanceRows.filter(r=>r.upah_hari).length}}/{{attendanceRows.length}} hadir</strong></div></div><el-table :data="attendanceRows" stripe><el-table-column prop="id_karyawan" label="ID" width="110"/><el-table-column prop="nama" label="Karyawan" min-width="190"/><el-table-column label="Kehadiran" width="150"><template #default="s"><el-button size="small" :type="s.row.upah_hari?'success':'info'" :plain="!s.row.upah_hari" @click="toggleHadir(s.row)">{{s.row.upah_hari?'Hadir':'Tidak Hadir'}}</el-button></template></el-table-column><el-table-column label="Tgl Merah" width="125"><template #default="s"><el-input-number v-model="s.row.tambahan_tgl_merah" :min="0" :max="1" :step="1"/></template></el-table-column><el-table-column label="Makan Lembur" width="140"><template #default="s"><el-input-number v-model="s.row.uang_makan_lembur" :min="0" :max="1" :step="1"/></template></el-table-column><el-table-column label="Lembur Malam" width="140"><template #default="s"><el-input-number v-model="s.row.lembur_malam" :min="0" :max="1" :step="1"/></template></el-table-column><el-table-column label="Jam Lembur" width="140"><template #default="s"><el-input-number v-model="s.row.lembur_jam" :min="0" :step="0.5"/></template></el-table-column><el-table-column label="Keterangan" min-width="180"><template #default="s"><el-input v-model="s.row.keterangan"/></template></el-table-column></el-table></el-card>
    </template>

    <template v-else>
     <el-card v-if="active==='transfer'" shadow="never" class="panel compact-form"><div class="transfer-summary"><span>Target netto <strong>{{rupiah(summary.target_netto||0)}}</strong></span><span>Sudah transfer <strong>{{rupiah(summary.total_transfer||0)}}</strong></span><span>Selisih <strong>{{rupiah(summary.selisih_transfer||0)}}</strong></span></div><el-form label-position="top" class="form-grid five"><el-form-item label="No. Referensi"><el-input v-model="transferForm.no_referensi"/></el-form-item><el-form-item label="Tanggal"><el-date-picker v-model="transferForm.tanggal" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="Nominal"><el-input-number v-model="transferForm.nominal" :min="0" controls-position="right"/></el-form-item><el-form-item label="Bank"><el-input v-model="transferForm.bank"/></el-form-item><el-form-item><el-button type="primary" :loading="saving" @click="withSaving(createTransfer)">Tambah Transfer</el-button></el-form-item></el-form></el-card>
     <el-card v-if="active==='potongan'||active==='kasbon'" shadow="never" class="panel compact-form"><el-form label-position="top" class="form-grid five"><el-form-item label="Karyawan"><el-select v-model="simpleForm.id_karyawan" filterable placeholder="Pilih"><el-option v-for="e in employees" :key="e.id_karyawan" :label="e.id_karyawan + ' · ' + e.nama + (e.status_aktif ? '' : ' (nonaktif)')" :value="e.id_karyawan"/></el-select></el-form-item><el-form-item :label="active==='kasbon'?'Jenis Kasbon':'Nama Potongan'"><el-input v-model="simpleForm.nama"/></el-form-item><el-form-item v-if="active==='kasbon'" label="Tanggal"><el-date-picker v-model="simpleForm.tanggal" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="Nominal"><el-input-number v-model="simpleForm.nominal" :min="0" controls-position="right"/></el-form-item><el-form-item label="Keterangan"><el-input v-model="simpleForm.keterangan"/></el-form-item><el-form-item><el-button type="primary" :loading="saving" @click="withSaving(()=>createSimple(active as 'potongan'|'kasbon'))">Simpan</el-button></el-form-item></el-form></el-card>
     <el-card v-if="active==='thr'" shadow="never" class="panel notice-card"><div><el-icon><Present/></el-icon><div><strong>THR dibayarkan terpisah</strong><p>Perhitungan ini tidak digabungkan dengan transfer payroll reguler.</p></div></div><el-button type="primary" :loading="saving" @click="withSaving(calculateThr)">Hitung THR Otomatis</el-button></el-card>
     <el-card v-if="active==='laporan'" shadow="never" class="panel compact-form"><div class="report-controls"><el-radio-group v-model="reportType" @change="loadPage"><el-radio-button value="internal">Internal</el-radio-button><el-radio-button value="konsultan">Konsultan</el-radio-button></el-radio-group><el-button @click="printPage"><el-icon><Printer/></el-icon>Cetak</el-button></div></el-card>
     <el-card shadow="never" class="panel table-panel"><div class="table-toolbar"><div><span>DATA {{current.label.toUpperCase()}}</span><strong>{{data.length}} baris</strong></div><el-button circle aria-label="Muat ulang data" @click="loadPage"><el-icon><Refresh/></el-icon></el-button></div><el-table v-if="active==='karyawan'" v-loading="loading" :data="data" stripe empty-text="Belum ada karyawan"><el-table-column prop="id_karyawan" label="ID" width="110"/><el-table-column prop="nama" label="Nama" min-width="200"/><el-table-column prop="kode_bagian" label="Bagian" width="110"/><el-table-column prop="jabatan" label="Jabatan" min-width="140"><template #default="s">{{s.row.jabatan||'—'}}</template></el-table-column><el-table-column label="Tipe" width="110"><template #default="s"><el-tag effect="light">{{s.row.tipe_gaji}}</el-tag></template></el-table-column><el-table-column label="Upah / Gaji" min-width="140" align="right"><template #default="s">{{rupiah(s.row.tipe_gaji==='bulanan'?s.row.gaji_bulanan:s.row.upah_harian)}}</template></el-table-column><el-table-column label="Uang Makan" min-width="130" align="right"><template #default="s">{{rupiah(s.row.uang_makan_hari)}}</template></el-table-column><el-table-column label="PTKP" width="90"><template #default="s">{{s.row.ptkp||'—'}}</template></el-table-column><el-table-column label="Masuk" width="120"><template #default="s">{{s.row.tgl_awal_kerja||'—'}}</template></el-table-column><el-table-column label="Status" width="110"><template #default="s"><el-tag :type="s.row.status_aktif?'success':'info'" effect="light">{{s.row.status_aktif?'Aktif':'Nonaktif'}}</el-tag></template></el-table-column><el-table-column label="Aksi" width="190" fixed="right"><template #default="s"><el-button text type="primary" @click="editEmployee(s.row)">Edit</el-button><el-button v-if="s.row.status_aktif" text type="danger" @click="deleteEmployee(s.row)">Nonaktifkan</el-button></template></el-table-column></el-table><el-table v-else v-loading="loading" :data="data" stripe :show-summary="active==='rekap'||active==='laporan'" :summary-method="summaryMethod" empty-text="Belum ada data untuk ditampilkan"><el-table-column v-for="col in columns" :key="col" :prop="col" :label="formatLabel(col)" min-width="150"><template #default="s"><el-tag v-if="col==='status'||col==='tipe_gaji'" effect="light">{{s.row[col]}}</el-tag><span v-else-if="typeof s.row[col]==='number'&&/nominal|jumlah|upah|gaji|total|bersih|potongan|transfer|selisih|makan|merah/.test(col)">{{rupiah(s.row[col])}}</span><span v-else>{{s.row[col]??'—'}}</span></template></el-table-column><el-table-column v-if="['backup','kasbon','slip','transfer','potongan'].includes(active)" label="Aksi" width="220" fixed="right"><template #default="s"><el-button v-if="active==='backup'" text type="warning" @click="restoreBackup(s.row)">Restore</el-button><template v-else-if="active==='kasbon'"><el-button text type="primary" @click="allocateKasbon(s.row)">Alokasikan</el-button><el-button v-if="s.row.status!=='lunas'" text type="warning" @click="settleKasbon(s.row)">Lunasi</el-button></template><el-button v-else-if="active==='transfer'" text type="danger" @click="deleteItem('transfer',s.row)">Hapus</el-button><el-button v-else-if="active==='potongan'" text type="danger" @click="deleteItem('potongan',s.row)">Hapus</el-button><el-button v-else text type="primary" @click="printSlip(s.row)">Cetak Slip</el-button></template></el-table-column></el-table></el-card>
    </template>
   </main>
  </div>
  <div v-if="mobileNav" class="backdrop" @click="mobileNav=false"></div>
 </div>

 <el-dialog v-model="employeeDialog" :title="editingEmployee?'Edit Karyawan':'Tambah Karyawan'" width="min(720px,94vw)"><el-form label-position="top"><div class="form-grid two"><el-form-item label="ID Karyawan"><el-input v-model="employee.id_karyawan" :disabled="!!editingEmployee" placeholder="Contoh: TK001"/></el-form-item><el-form-item label="Nama"><el-input v-model="employee.nama"/></el-form-item><el-form-item label="Tipe Gaji"><el-select v-model="employee.tipe_gaji"><el-option label="Harian" value="harian"/><el-option label="Bulanan" value="bulanan"/></el-select></el-form-item><el-form-item label="Kode Bagian"><el-input v-model="employee.kode_bagian" placeholder="PRO / FIN / LAS / KTR"/></el-form-item><el-form-item label="Jabatan"><el-input v-model="employee.jabatan"/></el-form-item><el-form-item label="Policy"><el-select v-model="employee.policy_code" clearable><el-option label="Normal" value=""/><el-option label="Tanpa Lembur" value="NO_LEMBUR"/></el-select></el-form-item><el-form-item v-if="employee.tipe_gaji==='harian'" label="Upah Harian"><el-input-number v-model="employee.upah_harian" :min="0" controls-position="right"/></el-form-item><el-form-item v-else label="Gaji Bulanan"><el-input-number v-model="employee.gaji_bulanan" :min="0" controls-position="right"/></el-form-item><el-form-item label="Uang Makan/Hari"><el-input-number v-model="employee.uang_makan_hari" :min="0" controls-position="right"/></el-form-item><el-form-item label="PTKP"><el-input v-model="employee.ptkp" placeholder="TK/0, K/1, ... (opsional)"/></el-form-item><el-form-item label="Tanggal Awal Kerja"><el-date-picker v-model="employee.tgl_awal_kerja" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="Tanggal Akhir Kerja"><el-date-picker v-model="employee.tgl_akhir_kerja" value-format="YYYY-MM-DD" placeholder="Kosongkan bila masih bekerja"/></el-form-item><el-form-item label="Status"><el-switch v-model="employee.status_aktif" :active-value="1" :inactive-value="0" active-text="Aktif" inactive-text="Nonaktif"/></el-form-item><el-form-item label="Catatan" class="span-2"><el-input v-model="employee.catatan" type="textarea" :rows="2" placeholder="Opsional"/></el-form-item></div></el-form><template #footer><el-button @click="employeeDialog=false">Batal</el-button><el-button type="primary" :loading="saving" @click="withSaving(saveEmployee)">Simpan Karyawan</el-button></template></el-dialog>
 <el-dialog v-model="periodDialog" title="Buat Periode Baru" width="min(640px,94vw)"><el-form label-position="top"><div class="form-grid two"><el-form-item label="Bulan"><el-select v-model="newPeriod.bulan"><el-option v-for="(b,i) in BULAN" :key="b" :label="labelBulan(b)" :value="i+1"/></el-select></el-form-item><el-form-item label="Tahun"><el-input-number v-model="newPeriod.tahun" :min="2000" :max="2100" :step="1" controls-position="right"/></el-form-item></div><div class="period-preview">Periode yang akan dibuat: <strong>{{BULAN[newPeriod.bulan-1]}} {{newPeriod.tahun}}</strong> — tanggal 1 sampai akhir bulan. Sistem akan menolak jika periode ini sudah ada.</div></el-form><template #footer><el-button @click="periodDialog=false">Batal</el-button><el-button type="primary" :loading="saving" @click="withSaving(savePeriod)">Buat Periode</el-button></template></el-dialog>
</template>

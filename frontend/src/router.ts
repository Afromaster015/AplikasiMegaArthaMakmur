import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  ['dashboard','/'], ['karyawan','/karyawan'], ['bagian','/bagian'], ['aturan','/aturan'], ['periode','/periode'], ['kehadiran','/kehadiran'],
  ['rekap','/rekap'], ['transfer','/transfer'], ['potongan','/potongan'], ['kasbon','/kasbon'],
  ['thr','/thr'], ['slip','/slip'], ['laporan','/laporan'], ['backup','/backup'], ['log','/audit-log']
].map(([name,path]) => ({ name, path, component: { template: '<span class="route-anchor" />' } }))

export default createRouter({ history: createWebHistory(), routes })

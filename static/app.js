'use strict';
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = cents => (cents / 100).toLocaleString('pt-BR', {style:'currency',currency:'BRL'});
const date = value => new Date(value).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'});
const statusNames = {draft:'Rascunho',completed:'Finalizado',cancelled:'Cancelado'};
const statusBadge = status => `<span class="badge ${status==='completed'?'green':status==='cancelled'?'red':''}">${statusNames[status]}</span>`;
let state = {products:[],suppliers:[],orders:[],movements:[]};
let editing = null, lines = [], toastTimer, currentUser = null, setupRequired = false;
const roleNames={admin:'Administrador',operator:'Operador',viewer:'Consulta'};
const pages={products:1,suppliers:1,orders:1,movements:1};
const PAGE_SIZE=10;
const titles = {users:['Usuários','Acesso organizado para cada responsabilidade.'],reports:['Relatórios','Transforme seus registros em informação.'],dashboard:['Tudo sob controle.','Seu estoque e seus pedidos, no mesmo lugar.'],products:['Produtos','Mantenha seu catálogo organizado e acompanhe os saldos.'],suppliers:['Fornecedores','Uma base organizada para as suas compras.'],orders:['Pedidos','Monte, revise e finalize suas vendas.'],movements:['Movimentações','Cada entrada e saída registrada, sem perder o histórico.']};

async function request(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':currentUser?.csrf||''},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) {if(response.status===401)showLogin(false);throw new Error(result.error || 'Não foi possível concluir a operação.');}
  return result;
}
async function refresh() {
  state = await request('/api/state');
  $('error').hidden = true;
  render();
  if(currentUser?.role==='admin')await renderUsers();
  applyPermissions();
}
function showError(error) { $('error').textContent=error.message; $('error').hidden=false; }
function toast(message) {
  clearTimeout(toastTimer);$('toast').textContent=message;$('toast').hidden=false;
  toastTimer=setTimeout(()=>$('toast').hidden=true,3500);
}
function view(name) {
  document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==name);
  document.querySelectorAll('nav button').forEach(el=>el.classList.toggle('active',el.dataset.view===name));
  $('page-title').textContent=titles[name][0];$('subtitle').textContent=titles[name][1];
  $('breadcrumb').textContent=name==='dashboard'?'VISÃO GERAL':titles[name][0].toUpperCase();
}
function empty(columns, message) {return `<tr><td colspan="${columns}" class="empty">${message}</td></tr>`;}
function render() {
  const active=state.products.filter(p=>p.active), low=active.filter(p=>p.stock<=p.minimum);
  const completed=state.orders.filter(o=>o.status==='completed');
  $('metrics').innerHTML=[['Produtos ativos',active.length,'Itens disponíveis no catálogo'],['Valor em estoque',money(state.products.reduce((s,p)=>s+p.stock*p.price_cents,0)),'Saldo × preço de venda cadastrado'],['Pedidos em aberto',state.orders.filter(o=>o.status==='draft').length,'Rascunhos aguardando finalização'],['Vendas finalizadas',money(completed.reduce((s,o)=>s+o.total_cents,0)),`${completed.length} pedido(s), sem cancelados`]].map(([label,value,detail])=>`<article class="metric"><p>${label}</p><strong>${value}</strong><small>${detail}</small></article>`).join('');
  $('low-stock').innerHTML=low.length?low.map(p=>`<div class="list-row"><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.sku)} · Mínimo: ${p.minimum}</small></div><span class="badge ${p.stock===0?'red':'amber'}">${p.stock} un.</span></div>`).join(''):'<div class="empty">Nenhum produto precisa de reposição.</div>';
  $('recent-orders').innerHTML=state.orders.length?state.orders.slice(0,5).map(o=>`<div class="list-row"><div><strong>#${o.id} · ${escapeHtml(o.customer)}</strong><small>${money(o.total_cents)}</small></div>${statusBadge(o.status)}</div>`).join(''):'<div class="empty">Seus próximos pedidos aparecerão aqui.</div>';
  renderProducts();renderOrders();
  renderSuppliers();
  const selected=$('movement-filter').value;
  $('movement-filter').innerHTML='<option value="">Todos os produtos</option>'+state.products.map(p=>`<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
  $('movement-filter').value=selected;renderMovements();
}
function renderProducts() {
  const query=$('product-search').value.toLocaleLowerCase('pt-BR');
  $('product-rows').innerHTML=paginate('products',state.products.filter(p=>(p.name+' '+p.sku).toLocaleLowerCase('pt-BR').includes(query)).filter(p=>!$('product-status').value||($('product-status').value==='active'?p.active:$('product-status').value==='inactive'?!p.active:p.active&&p.stock<=p.minimum))).map(p=>`<tr><td class="wrap"><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.sku)}</small></td><td class="wrap">${escapeHtml(state.suppliers.find(s=>s.id===p.supplier_id)?.name)||'—'}</td><td>${money(p.price_cents)}</td><td><span class="badge ${p.stock<=p.minimum?'amber':'green'}">${p.stock} / ${p.minimum}</span></td><td>${p.active?'Ativo':'Inativo'}</td><td><div class="actions"><button data-edit="products" data-id="${p.id}">Editar</button><button data-toggle="products" data-id="${p.id}">${p.active?'Desativar':'Reativar'}</button></div></td></tr>`).join('')||empty(6,'Nenhum produto encontrado. Cadastre seu primeiro item.');
}
function renderOrders() {
  const filter=$('order-filter').value;
  $('order-rows').innerHTML=paginate('orders',state.orders.filter(o=>!filter||o.status===filter).filter(o=>(o.customer+' '+o.id).toLocaleLowerCase('pt-BR').includes($('order-search').value.toLocaleLowerCase('pt-BR')))).map(o=>`<tr><td><strong>#${String(o.id).padStart(4,'0')}</strong><small>${date(o.created_at)}</small></td><td class="wrap">${escapeHtml(o.customer)}</td><td>${money(o.total_cents)}</td><td>${statusBadge(o.status)}</td><td><div class="actions"><button data-edit="orders" data-id="${o.id}">${o.status==='draft'?'Editar':'Detalhes'}</button>${o.status==='draft'?`<button data-action="complete" data-id="${o.id}">Finalizar</button>`:''}${o.status!=='cancelled'?`<button class="danger" data-action="cancel" data-id="${o.id}">Cancelar</button>`:''}</div></td></tr>`).join('')||empty(5,'Nenhum pedido neste status.');
}
function renderMovements() {
  const filter=$('movement-filter').value;
  $('movement-rows').innerHTML=paginate('movements',state.movements.filter(m=>!filter||m.product_id===Number(filter)).filter(m=>inPeriod(m.created_at,$('movement-start').value,$('movement-end').value))).map(m=>`<tr><td>${date(m.created_at)}</td><td class="wrap">${escapeHtml(state.products.find(p=>p.id===m.product_id)?.name)}</td><td class="${m.quantity>0?'positive':'negative'}">${m.quantity>0?'+':''}${m.quantity}</td><td>${m.balance}</td><td class="wrap">${escapeHtml(m.reason)}</td><td>${m.order_id?'#'+m.order_id:'Manual'}</td></tr>`).join('')||empty(6,'Nenhuma movimentação registrada.');
}
function field(label,name,value='',type='text',extras='') {
  return `<label>${label}<input name="${name}" type="${type}" value="${escapeHtml(value)}" ${extras}></label>`;
}
function openEditor(kind,id) {
  const record=id?state[kind].find(r=>r.id===id):null;
  if(currentUser?.role==='viewer'&&kind!=='orders'&&kind!=='password')return;
  editing={kind,id};$('form-error').hidden=true;$('save-button').hidden=false;$('save-button').disabled=false;
  $('save-button').textContent='Salvar';
  $('modal-title').textContent=({users:'Usuário',password:'Trocar senha',products:'Produto',suppliers:'Fornecedor',orders:'Pedido',movements:'Movimentação'})[kind]+(id?' #'+id:' • novo');
  if(kind==='users') {
    $('form-content').innerHTML=`<div class="form-grid">${field('Nome','name','','text','required maxlength="80"')}${field('Usuário','username','','text','required minlength="3" maxlength="40" pattern="[a-z0-9._-]{3,40}" autocomplete="off"')}${field('Senha inicial (mínimo 10 caracteres)','password','','password','required minlength="10" maxlength="128" autocomplete="new-password"')}<label>Perfil<select name="role"><option value="operator">Operador</option><option value="viewer">Consulta</option><option value="admin">Administrador</option></select></label></div><p class="hint">Operador gerencia a operação. Consulta só visualiza e exporta. Administrador também gerencia usuários.</p>`;
  } else if(kind==='password') {
    $('form-content').innerHTML=field('Senha atual','current_password','','password','required maxlength="128" autocomplete="current-password"')+field('Nova senha','new_password','','password','required minlength="10" maxlength="128" autocomplete="new-password"')+'<p class="hint">Após salvar, entre novamente com a nova senha. Todas as suas sessões serão encerradas.</p>';
  } else if(kind==='suppliers') {
    $('form-content').innerHTML=`<div class="form-grid">${field('Nome do fornecedor','name',record?.name,'text','required maxlength="160"')}${field('Contato (opcional)','contact',record?.contact,'text','maxlength="160"')}</div>`;
  } else if(kind==='products') {
    $('form-content').innerHTML=`<div class="form-grid">${field('Nome do produto','name',record?.name,'text','required maxlength="160"')}${field('SKU / código único','sku',record?.sku,'text','required maxlength="40"')}${field('Preço de venda (R$)','price',record?(record.price_cents/100).toFixed(2):'','number','required min="0" max="1000000" step="0.01"')}${field('Estoque mínimo (unidades)','minimum',record?.minimum??0,'number','required min="0" max="100000000" step="1"')}<label class="full">Fornecedor<select name="supplier_id"><option value="">Sem fornecedor</option>${state.suppliers.filter(s=>s.active||s.id===record?.supplier_id).map(s=>`<option value="${s.id}" ${s.id===record?.supplier_id?'selected':''}>${escapeHtml(s.name)}${s.active?'':' (inativo)'}</option>`).join('')}</select></label></div><p class="hint">O saldo é alterado somente por movimentações e pedidos, preservando o histórico.</p>`;
  } else if(kind==='movements') {
    $('form-content').innerHTML=`<div class="form-grid"><label class="full">Produto<select name="product_id" required><option value="">Selecione</option>${state.products.filter(p=>p.active).map(p=>`<option value="${p.id}">${escapeHtml(p.name)} · saldo ${p.stock}</option>`).join('')}</select></label><label>Tipo<select name="kind"><option value="in">Entrada</option><option value="out">Saída</option></select></label>${field('Quantidade (unidades)','quantity',1,'number','required min="1" max="100000000" step="1"')}<div class="full">${field('Motivo','reason','','text','required maxlength="240" placeholder="Ex.: recebimento de compra"')}</div></div>`;
  } else if(kind==='orders' && record && (record.status!=='draft'||currentUser?.role==='viewer')) {
    $('save-button').hidden=true;
    $('form-content').innerHTML=`<div class="status-note">${statusBadge(record.status)}</div><h2>${escapeHtml(record.customer)}</h2><p class="hint">${date(record.created_at)} · Preços registrados no pedido</p><div class="detail-lines"><table><thead><tr><th>Produto</th><th>Qtd.</th><th>Unitário</th><th>Total</th></tr></thead><tbody>${record.items.map(i=>`<tr><td>${escapeHtml(i.name)}<small>${escapeHtml(i.sku)}</small></td><td>${i.quantity}</td><td>${money(i.price_cents)}</td><td>${money(i.quantity*i.price_cents)}</td></tr>`).join('')}</tbody></table></div><div class="order-total"><span>Total</span><strong>${money(record.total_cents)}</strong></div>`;
  } else {
    lines=record?record.items.map(i=>({...i})):[{product_id:'',quantity:1}];
    $('form-content').innerHTML=field('Nome do cliente','customer',record?.customer,'text','required maxlength="160"')+'<p class="hint">Rascunhos não reservam estoque. A baixa acontece ao finalizar. Todos os produtos são vendidos por unidade.</p><div id="order-lines"></div><button type="button" id="add-line" class="add-line">+ Adicionar item</button><div class="order-total"><span>Total do pedido</span><strong id="order-total"></strong></div>';
    renderLines();
  }
  $('editor').showModal();
}
function linePrice(line) {
  const original=editing.id?state.orders.find(o=>o.id===editing.id)?.items.find(i=>i.product_id===Number(line.product_id)):null;
  return original?.price_cents??state.products.find(p=>p.id===Number(line.product_id))?.price_cents??0;
}
function renderLines() {
  $('order-lines').innerHTML=lines.map((line,index)=>`<div class="order-line"><label>Produto<select data-line="${index}" data-field="product_id" required><option value="">Selecione</option>${state.products.filter(p=>p.active||p.id===Number(line.product_id)).map(p=>`<option value="${p.id}" ${p.id===Number(line.product_id)?'selected':''}>${escapeHtml(p.name)} · ${p.stock} un.${p.active?'':' (inativo)'}</option>`).join('')}</select></label><label>Qtd.<input data-line="${index}" data-field="quantity" type="number" min="1" max="100000000" step="1" value="${escapeHtml(line.quantity)}" required></label><span class="line-price" id="line-price-${index}">${money(linePrice(line)*Number(line.quantity))}</span><button type="button" data-remove-line="${index}" aria-label="Remover item ${index+1}">×</button></div>`).join('');
  updateTotal();
}
function updateTotal() {
  lines.forEach((line,index)=>{$('line-price-'+index).textContent=money(linePrice(line)*(Number(line.quantity)||0));});
  $('order-total').textContent=money(lines.reduce((sum,line)=>sum+linePrice(line)*(Number(line.quantity)||0),0));
}
$('editor-form').addEventListener('input',event=>{
  if(event.target.dataset.line!==undefined) {
    lines[Number(event.target.dataset.line)][event.target.dataset.field]=Number(event.target.value);updateTotal();
  }
});
$('editor-form').addEventListener('submit',async event=>{
  event.preventDefault();if($('save-button').hidden)return;
  const form=new FormData(event.currentTarget);let data=Object.fromEntries(form);
  if(editing.kind==='products')data={...data,price_cents:Math.round(Number(data.price)*100),minimum:Number(data.minimum),supplier_id:data.supplier_id?Number(data.supplier_id):null};
  if(editing.kind==='movements')data={...data,quantity:Number(data.quantity),product_id:Number(data.product_id)};
  if(editing.kind==='orders')data={customer:data.customer,items:lines.map(l=>({product_id:Number(l.product_id),quantity:Number(l.quantity)}))};
  $('save-button').disabled=true;$('form-error').hidden=true;
  try {
    await request(editing.kind==='password'?'/api/auth/password':'/api/'+editing.kind+(editing.id?'/'+editing.id:''),data);
    if(editing.kind==='password'){$('editor').close();toast('Senha alterada. Entre novamente.');await boot();return;}
    $('editor').close();toast('Registro salvo com sucesso.');await refresh();
  } catch(error) {
    if($('editor').open){$('form-error').textContent=error.message;$('form-error').hidden=false;}else showError(error);
  } finally {$('save-button').disabled=false;}
});
$('close-modal').addEventListener('click',()=>$('editor').close());
$('cancel-modal').addEventListener('click',()=>$('editor').close());
$('product-search').addEventListener('input',()=>{pages.products=1;renderProducts();applyPermissions();});
$('order-filter').addEventListener('change',()=>{pages.orders=1;renderOrders();applyPermissions();});
$('movement-filter').addEventListener('change',()=>{pages.movements=1;renderMovements();});
document.addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.view)return view(button.dataset.view);
  if(button.dataset.new)return openEditor(button.dataset.new);
  if(button.dataset.edit)return openEditor(button.dataset.edit,Number(button.dataset.id));
  if(button.id==='add-line'){lines.push({product_id:'',quantity:1});renderLines();return;}
  if(button.dataset.removeLine!==undefined){lines.splice(Number(button.dataset.removeLine),1);renderLines();return;}
  if(button.dataset.toggle||button.dataset.action) {
    let path,payload={};
    if(button.dataset.toggle){
      const kind=button.dataset.toggle,record=state[kind].find(r=>r.id===Number(button.dataset.id));
      if(!confirm(`${record.active?'Desativar':'Reativar'} ${record.name}? O histórico será preservado.`))return;
      path=`/api/${kind}/${record.id}/active`;payload={active:!record.active};
    }else{
      if(!confirm(button.dataset.action==='complete'?'Finalizar pedido e baixar todos os itens do estoque?':'Cancelar pedido? Se já finalizado, o estoque será devolvido.'))return;
      path=`/api/orders/${button.dataset.id}/${button.dataset.action}`;
    }
    button.disabled=true;
    try{await request(path,payload);toast('Operação concluída.');await refresh();}catch(error){showError(error);}finally{button.disabled=false;}
  }
});
$('today').textContent=new Date().toLocaleDateString('pt-BR',{dateStyle:'long'});
boot().catch(error=>{$('auth-title').textContent='Não foi possível conectar';$('auth-error').textContent=error.message+' Confira se o servidor Python está aberto.';$('auth-error').hidden=false;});

function renderSuppliers(){
  $('supplier-rows').innerHTML=paginate('suppliers',state.suppliers.filter(s=>(s.name+' '+s.contact).toLocaleLowerCase('pt-BR').includes($('supplier-search').value.toLocaleLowerCase('pt-BR')))).map(s=>`<tr><td class="wrap"><strong>${escapeHtml(s.name)}</strong></td><td class="wrap">${escapeHtml(s.contact)||'—'}</td><td><span class="badge ${s.active?'green':''}">${s.active?'Ativo':'Inativo'}</span></td><td><div class="actions"><button data-edit="suppliers" data-id="${s.id}">Editar</button><button data-toggle="suppliers" data-id="${s.id}">${s.active?'Desativar':'Reativar'}</button></div></td></tr>`).join('')||empty(4,'Nenhum fornecedor. Clique em “Novo fornecedor” para começar.');

}

function paginate(kind,rows){
  const count=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));pages[kind]=Math.min(pages[kind],count);
  $(kind+'-pager').innerHTML=`<span>${rows.length} registro(s) · Página ${pages[kind]} de ${count}</span><div><button data-page="${kind}" data-delta="-1" ${pages[kind]===1?'disabled':''}>← Anterior</button><button data-page="${kind}" data-delta="1" ${pages[kind]===count?'disabled':''}>Próxima →</button></div>`;
  return rows.slice((pages[kind]-1)*PAGE_SIZE,pages[kind]*PAGE_SIZE);
}
function inPeriod(value,start,end){
  const d=new Date(value),local=[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
  return (!start||local>=start)&&(!end||local<=end);
}
function applyPermissions(){
  const viewer=currentUser?.role==='viewer';
  $('readonly-notice').hidden=!viewer;
  document.querySelectorAll('[data-new],[data-toggle],[data-action]').forEach(b=>b.hidden=viewer);
  document.querySelectorAll('[data-edit]').forEach(b=>{b.hidden=viewer&&b.dataset.edit!=='orders';if(viewer&&b.dataset.edit==='orders')b.textContent='Detalhes';});
  $('users-nav').hidden=currentUser?.role!=='admin';
}
function showLogin(setup){
  currentUser=null;setupRequired=setup;document.body.classList.add('locked');$('editor').close();
  $('auth-screen').hidden=false;$('auth-form').reset();$('setup-name').hidden=!setup;
  $('auth-form').elements.name.required=setup;
  $('auth-title').textContent=setup?'Seu primeiro acesso.':'Bem-vindo de volta.';
  $('auth-description').textContent=setup?'Crie a conta de administrador. Escolha uma senha com pelo menos 10 caracteres.':'Entre para continuar gerenciando sua operação.';
  $('auth-submit').textContent=setup?'Criar conta e entrar':'Entrar';
  $('auth-form').elements.password.minLength=setup?10:1;
  $('auth-form').elements.password.autocomplete=setup?'new-password':'current-password';
  $('auth-error').hidden=true;
}
async function boot(){
  const me=await request('/api/auth/me');
  if(!me.user){showLogin(me.setup_required);return;}
  currentUser=me.user;$('auth-screen').hidden=true;document.body.classList.remove('locked');
  $('user-label').textContent=currentUser.name+' · '+roleNames[currentUser.role];
  view('dashboard');await refresh();
}
$('auth-form').addEventListener('submit',async event=>{
  event.preventDefault();$('auth-submit').disabled=true;$('auth-error').hidden=true;
  try{await request(setupRequired?'/api/auth/setup':'/api/auth/login',Object.fromEntries(new FormData(event.currentTarget)));await boot();}
  catch(error){$('auth-error').textContent=error.message;$('auth-error').hidden=false;}
  finally{$('auth-submit').disabled=false;}
});
$('logout-button').addEventListener('click',async()=>{try{await request('/api/auth/logout',{});showLogin(false);}catch(error){showError(error);}});
$('password-button').addEventListener('click',()=>openEditor('password'));
$('refresh-button').addEventListener('click',async()=>{try{await refresh();toast('Dados atualizados.');}catch(error){showError(error);}});
async function renderUsers(){
  const result=await request('/api/users');
  $('user-rows').innerHTML=result.users.map(u=>`<tr><td>${escapeHtml(u.name)}</td><td>${escapeHtml(u.username)}</td><td>${roleNames[u.role]}</td><td>${u.active?'Ativo':'Inativo'}</td><td>${u.id===currentUser.id?'Sua conta':`<button data-user-active="${u.id}" data-active="${u.active?'false':'true'}">${u.active?'Desativar':'Reativar'}</button>`}</td></tr>`).join('');
}
for(const [id,kind,event,renderer] of [['product-status','products','change',renderProducts],['supplier-search','suppliers','input',renderSuppliers],['order-search','orders','input',renderOrders],['movement-start','movements','change',renderMovements],['movement-end','movements','change',renderMovements]]){
  $(id).addEventListener(event,()=>{pages[kind]=1;renderer();applyPermissions();});
}
document.addEventListener('click',async event=>{
  const b=event.target.closest('button');if(!b)return;
  if(b.dataset.page){pages[b.dataset.page]+=Number(b.dataset.delta);({products:renderProducts,suppliers:renderSuppliers,orders:renderOrders,movements:renderMovements})[b.dataset.page]();applyPermissions();}
  if(b.dataset.userActive){
    b.disabled=true;
    try{await request('/api/users/'+b.dataset.userActive+'/active',{active:b.dataset.active==='true'});await renderUsers();toast('Acesso atualizado.');}catch(error){showError(error);}finally{b.disabled=false;}
  }
});
// Campos de texto são protegidos contra fórmulas ao abrir o CSV em planilhas.
function csvCell(value){
  let s=String(value??'');if(typeof value==='string'&&/^[\s]*[=+@-]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
}
function exportReport(){
  const type=$('report-type').value,start=$('report-start').value,end=$('report-end').value,status=$('report-status').value;
  if(type!=='products'&&start&&end&&start>end){$('report-result').textContent='A data inicial deve ser anterior ou igual à final.';return;}
  const decimal=c=>(c/100).toFixed(2).replace('.',',');let header,rows;
  if(type==='products'){
    header=['SKU','Produto','Fornecedor','Preço de venda (R$)','Saldo','Mínimo','Status'];
    rows=state.products.map(p=>[p.sku,p.name,state.suppliers.find(s=>s.id===p.supplier_id)?.name||'',decimal(p.price_cents),p.stock,p.minimum,p.active?'Ativo':'Inativo']);
  }else if(type==='orders'){
    header=['Pedido','Criado em (local)','Cliente','Status','Total (R$)'];
    rows=state.orders.filter(o=>inPeriod(o.created_at,start,end)&&(!status||o.status===status)).map(o=>[o.id,date(o.created_at),o.customer,statusNames[o.status],decimal(o.total_cents)]);
  }else{
    header=['Movimento','Data (local)','Produto','Variação','Saldo após','Motivo','Pedido'];
    rows=state.movements.filter(m=>inPeriod(m.created_at,start,end)).map(m=>[m.id,date(m.created_at),state.products.find(p=>p.id===m.product_id)?.name||'',m.quantity,m.balance,m.reason,m.order_id||'']);
  }
  const blob=new Blob(['\uFEFF'+[header,...rows].map(r=>r.map(csvCell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='estoca-'+type+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('report-result').textContent=rows.length+' registro(s) exportado(s).';
}
$('export-button').addEventListener('click',async()=>{try{await refresh();exportReport();}catch(error){showError(error);}});

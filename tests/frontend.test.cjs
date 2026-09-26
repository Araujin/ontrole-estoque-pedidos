// Verificações com DOM mínimo; não substituem testes visuais em navegador.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');

async function load(){
  const elements=new Map();
  const make=(id)=>{
    if(elements.has(id))return elements.get(id);
    let html='';
    const el={id,value:'',hidden:false,disabled:false,textContent:'',open:false,
      dataset:{},classList:{add(){},remove(){},toggle(){}},addEventListener(){},
      showModal(){this.open=true},close(){this.open=false},reset(){},click(){},
      elements:{name:{},password:{}}};
    Object.defineProperty(el,'innerHTML',{get:()=>html,set:v=>{html=v;for(const m of v.matchAll(/id="([^"]+)"/g))make(m[1]);}});
    elements.set(id,el);return el;
  };
  const html=fs.readFileSync(path.join(root,'static/index.html'),'utf8');
  for(const m of html.matchAll(/id="([^"]+)"/g))make(m[1]);
  const product={id:1,name:'<Teste>',sku:'P1',price_cents:1990,stock:10,minimum:2,active:1,supplier_id:1};
  const snapshot={products:[product],suppliers:[{id:1,name:'Fornecedor',contact:'',active:1}],orders:[{id:1,customer:'Cliente',status:'draft',total_cents:3980,created_at:'2026-09-26T12:00:00Z',items:[{product_id:1,name:'<Teste>',sku:'P1',quantity:2,price_cents:1990}]}],movements:[]};
  const context=vm.createContext({console,Intl,Date,Number,String,Math,Map,Set,Blob,URL,
    setTimeout(){},clearTimeout(){},confirm:()=>true,
    document:{getElementById:id=>{if(!elements.has(id))throw new Error('ID inexistente: '+id);return elements.get(id)},querySelectorAll:()=>[],addEventListener(){},body:{classList:{add(){},remove(){}}},createElement:()=>({click(){}})},
    fetch:async url=>({ok:true,status:200,json:async()=>url==='/api/auth/me'?{user:{id:1,name:'Admin',role:'admin',csrf:'x'},setup_required:false}:url==='/api/users'?{users:[]}:snapshot})});
  vm.runInContext(fs.readFileSync(path.join(root,'static/app.js'),'utf8'),context);
  await new Promise(setImmediate);await new Promise(setImmediate);
  return {run:code=>vm.runInContext(code,context),elements};
}
test('inicialização autenticada renderiza painel e tabelas',async()=>{
  const a=await load();assert.match(a.elements.get('product-rows').innerHTML,/&lt;Teste&gt;/);
  assert.match(a.elements.get('metrics').innerHTML,/Produtos ativos/);
  assert.equal(a.elements.get('auth-screen').hidden,true);
});
test('editores abrem sem referências de elementos ausentes',async()=>{
  const a=await load();
  for(const type of ['products','suppliers','orders','movements','users','password']){
    a.run(`openEditor('${type}')`);assert.equal(a.elements.get('editor').open,true);
  }
  a.run("openEditor('orders',1)");assert.match(a.elements.get('order-lines').innerHTML,/&lt;Teste&gt;/);
});
test('paginação limita a dez registros e filtros funcionam',async()=>{
  const a=await load();assert.equal(a.run("paginate('products',Array.from({length:25},(_,i)=>i)).length"),10);
  a.run('pages.products=3');assert.equal(a.run("paginate('products',Array.from({length:25},(_,i)=>i))[0]"),20);
  a.elements.get('product-search').value='inexistente';a.run('renderProducts()');
  assert.match(a.elements.get('product-rows').innerHTML,/Nenhum produto/);
});
test('CSV escapa fórmulas, aspas e preserva números negativos',async()=>{
  const a=await load();assert.equal(a.run('csvCell("=1+1")'),'"\'=1+1"');
  assert.equal(a.run('csvCell(-2)'),'"-2"');
  assert.equal(a.run('csvCell(\'a"b\')'),'"a""b"');
});
test('consulta abre detalhes sem formulário editável',async()=>{
  const a=await load();a.run("currentUser.role='viewer';openEditor('orders',1)");
  assert.equal(a.elements.get('save-button').hidden,true);
});

function cConj([r,i]){return[r,-i];}
function cAbs2([r,i]){return r*r+i*i;}

class AerSimulator {
  constructor({shots=1024,noiseModel=null}={}){
    this.shots=shots; this.noiseModel=noiseModel;
  }
  run(circuit){
    let sv=circuit._sv.map(c=>[...c]);
    if(this.noiseModel&&this.noiseModel.type==='depolarising'){
      sv=this._depolarise(sv,this.noiseModel.p);
    }
    return new AerResult(sv,this.shots);
  }
  _depolarise(sv,p){
    const r=Math.random();
    if(r<p/4)  return applyX_sv(sv);
    if(r<p/2)  return applyY_sv(sv);
    if(r<3*p/4)return applyZ_sv(sv);
    return sv;
  }
}

class AerResult {
  constructor(sv,shots){this._sv=sv;this.shots=shots;}
  get_statevector(){return this._sv;}
  get_counts(shots=this.shots){
    const probs=this._sv.map(cAbs2);
    const counts={};
    for(let s=0;s<shots;s++){
      let cum=0,r=Math.random(),out=probs.length-1;
      for(let i=0;i<probs.length;i++){cum+=probs[i];if(r<cum){out=i;break;}}
      counts[out]=(counts[out]||0)+1;
    }
    return counts;
  }
  state_fidelity(ref){
    let re=0,im=0;
    for(let i=0;i<this._sv.length;i++){
      const[rr,ri]=cConj(ref[i]);
      const[sr,si]=this._sv[i];
      re+=rr*sr-ri*si; im+=rr*si+ri*sr;
    }
    return re*re+im*im;
  }
}

// ── Gates ─────────────────────────────────────────────────────────────────────
const K_=1/Math.sqrt(2);
function applyH_sv([[r0,i0],[r1,i1]]){
  return[[K_*(r0+r1),K_*(i0+i1)],[K_*(r0-r1),K_*(i0-i1)]];
}
function applyX_sv(sv){return[[...sv[1]],[...sv[0]]];}
function applyY_sv([[r0,i0],[r1,i1]]){return[[i1,-r1],[-i0,r0]];}
function applyZ_sv([[r0,i0],[r1,i1]]){return[[r0,i0],[-r1,-i1]];}

// ── QuantumCircuit ────────────────────────────────────────────────────────────
class QuantumCircuit {
  constructor(){this._sv=[[1,0],[0,0]];}
  h(){this._sv=applyH_sv(this._sv);return this;}
  x(){this._sv=applyX_sv(this._sv);return this;}
  y(){this._sv=applyY_sv(this._sv);return this;}
  z(){this._sv=applyZ_sv(this._sv);return this;}
  copy(){const c=new QuantumCircuit();c._sv=this._sv.map(a=>[...a]);return c;}
}

// ── Reference state ───────────────────────────────────────────────────────────
const KET0_SV=[[1,0],[0,0]];

// ── makeToken ─────────────────────────────────────────────────────────────────
function makeToken(n){
  n=n||N_QUBITS||6;
  const circuits=[],basisKey=[],backend=new AerSimulator({shots:1024});
  for(let i=0;i<n;i++){
    const basis=Math.random()<0.5?'+':'x';
    basisKey.push(basis);
    const qc=new QuantumCircuit();
    if(basis==='+'){
      qc.h();          // |+⟩ = H|0⟩
    } else {
      qc.x().h();      // |−⟩ = H(X|0⟩)  ← FIXED (old was H→X→H = |0⟩)
    }
    circuits.push(qc);
  }
  return{circuits,basisKey,backend};
}

// ── measureToken ──────────────────────────────────────────────────────────────
function measureToken(token,strategy){
  const{circuits,basisKey,backend}=token;
  const scores=[],guessKey=[],counts_arr=[];
  for(let i=0;i<circuits.length;i++){
    let guess;
    if(strategy==='legit')      guess=basisKey[i];
    else if(strategy==='fixed') guess='+';
    else                        guess=Math.random()<0.5?'+':'x';
    guessKey.push(guess);

    const dec=circuits[i].copy();
    if(guess==='+'){
      dec.h();        // H† = H
    } else {
      dec.h().x();    // decode 'x': H then X  ← FIXED (old was X→H→H = |1⟩)
    }

    let be=backend;
    if(strategy==='clone'){
      be=new AerSimulator({shots:1024,
        noiseModel:{type:'depolarising',p:0.3+Math.random()*0.4}});
    }

    const result=be.run(dec);
    const fid=result.state_fidelity(KET0_SV);
    counts_arr.push(result.get_counts(1024));
    scores.push(Math.max(0,Math.min(1,fid)));
  }
  const avg=scores.reduce((a,b)=>a+b,0)/scores.length;
  return{scores,avg,guessKey,counts:counts_arr};
}
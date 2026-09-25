'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const M=require('../docs/assets/model.js');
const D=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/data/atlas.json'),'utf8'));
const close=(a,b,eps=1e-6)=>assert.ok(Math.abs(a-b)<eps,`${a} != ${b}`);
test('zero is not treated as missing; null and NaN are missing',()=>{
 assert.equal(M.bucket(0,[10,20]),0);
 for(const v of [null,undefined,NaN,Infinity]) assert.equal(M.bucket(v,[10,20]),-1);
 assert.equal(M.bucket(10,[10,20]),1); assert.equal(M.bucket(20,[10,20]),2);
});
test('search handles German diacritics',()=>{
 assert.equal(M.normalize('  Öhringen  '),'ohringen');
 assert.equal(M.normalize('Straße'),'strasse');
});

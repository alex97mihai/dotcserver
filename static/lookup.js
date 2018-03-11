function hideUsers() {
  var ul, li, a, i;
  ul = document.getElementById("myUL");
  li = ul.getElementsByTagName('li');
  for (i = 0; i < li.length; i++) {
    li[i].style.display = "none";
  }
}

function searchUser() {
  // Declare variables
  var input, filter, ul, li, a, i;
  input = document.getElementById('myInput');
  filter = input.value.toUpperCase();
  ul = document.getElementById("myUL");
  li = ul.getElementsByTagName('li');
  // Loop through all list items, and hide those who don't match the search query
  for (i = 0; i < li.length; i++) {
    a = li[i].getElementsByTagName("a")[0];
    li[i].style.display = "none";
    if (filter.length > 3 && a.innerHTML.toUpperCase().indexOf(filter) > -1) {
      li[i].style.display = "block";
    } else {
      li[i].style.display = "none";
    }
  }
}
